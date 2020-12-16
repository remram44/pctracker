from datetime import datetime
import logging
import pynput
import os
import sqlite3
import subprocess
import time


logger = logging.getLogger(__name__)


MAX_INACTIVE_TIME = 30#2 * 60


class InputMonitor(object):
    def __init__(self):
        self.mouse = pynput.mouse.Listener(
            on_move=self.on_input,
            on_click=self.on_input,
            on_scroll=self.on_input,
        )
        self.mouse.start()

        self.keyboard = pynput.keyboard.Listener(
            on_press=self.on_input,
            on_release=self.on_input,
        )
        self.keyboard.start()

        self.last_input = datetime.utcnow()

    def on_input(self, *args, **kwargs):
        self.last_input = datetime.utcnow()


def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Open database
    create_tables = not os.path.exists('database.sqlite3')
    database = sqlite3.connect('database.sqlite3')
    if create_tables:
        database.executescript(
            '''\
            CREATE TABLE runs(
                id INTEGER PRIMARY KEY,
                start DATETIME NOT NULL,
                end DATETIME NULL,
                end_reason TEXT NOT NULL DEFAULT ''
            );
            CREATE INDEX idx_runs_start ON runs(start);
            CREATE INDEX idx_runs_end ON runs(end);
            
            CREATE TABLE windows(
                id INTEGER PRIMARY KEY,
                start DATETIME NOT NULL,
                end DATETIME NOT NULL,
                active BOOLEAN NOT NULL,
                name TEXT NOT NULL
            );
            CREATE INDEX idx_windows_start ON windows(start);
            CREATE INDEX idx_windows_end ON windows(end);
            CREATE INDEX idx_windows_active ON windows(active) WHERE active=1;
            CREATE INDEX idx_windows_name ON windows(name);
            ''',
        )

    # Close previous runs
    unclosed_runs = database.execute(
        '''\
        SELECT id, start, end
        FROM runs
        WHERE end IS NULL;
        ''',
    )
    try:
        next(unclosed_runs)
    except StopIteration:
        # No unclosed run
        pass
    else:
        try:
            next(unclosed_runs)
        except StopIteration:
            # Only one, good
            pass
        else:
            raise RuntimeError("Multiple unclosed runs in database")

        # Close the run after the most recent event
        most_recent_events = list(database.execute(
            '''\
            SELECT end
            FROM windows
            ORDER BY end DESC
            LIMIT 1;
            ''',
        ))
        if not most_recent_events:  # Shouldn't happen
            database.execute(
                '''\
                UPDATE runs
                SET end = start, end_reason = 'stopped'
                WHERE end IS NULL;
                ''',
            )
        else:
            database.execute(
                '''\
                UPDATE runs
                SET end = ?, end_reason = 'stopped'
                WHERE end IS NULL;
                ''',
                most_recent_events[0],
            )

    # Monitor inputs
    input_monitor = InputMonitor()

    # Start run
    cursor = database.cursor()
    cursor.execute(
        '''\
        INSERT INTO runs(start)
        VALUES(datetime());
        ''',
    )
    current_run = cursor.lastrowid
    database.commit()

    current_windows = {}

    # Loop forever
    while True:
        time.sleep(5)

        # Check whether user has gone away
        inactive_time = (datetime.utcnow() - input_monitor.last_input)
        inactive_time = inactive_time.total_seconds()
        if inactive_time > MAX_INACTIVE_TIME:
            # He's gone
            if current_run is not None:
                logger.warning("Input inactive")

                # TODO: Erase events since he went away?

                # End run
                database.execute(
                    '''\
                    UPDATE runs
                    SET end=datetime(), end_reason = 'inactive'
                    WHERE id=?;
                    ''',
                    (current_run,)
                )
                database.commit()
                current_run = None
                current_windows = {}

            continue
        else:
            if current_run is None:
                logger.warning("Input active again")
                cursor = database.cursor()
                cursor.execute(
                    '''\
                    INSERT INTO runs(start)
                    VALUES(datetime());
                    ''',
                )
                current_run = cursor.lastrowid
                database.commit()

        active_id = get_active_window()
        window_ids = get_windows()

        extend_windows = []
        insert_windows = []
        for window_id in window_ids:
            name = get_window_name(window_id)
            active = window_id == active_id

            if window_id in current_windows:
                current = current_windows[window_id]
                if current[1] == (name, active):
                    extend_windows.append(current[0])
                else:
                    del current_windows[window_id]
                    insert_windows.append((window_id, name, active))
            else:
                insert_windows.append((window_id, name, active))

        for window_id, current in list(current_windows.items()):
            if window_id not in window_ids:
                del current_windows[window_id]

        # Insert into database
        cursor = database.cursor()
        if extend_windows:
            logger.info("extend %d", len(extend_windows))
            cursor.executemany(
                '''\
                UPDATE windows
                SET end=datetime()
                WHERE id=?;
                ''',
                ((i,) for i in extend_windows),
            )
        if insert_windows:
            for window_id, name, active in insert_windows:
                logger.info("insert %s %s", ('Y' if active else 'n'), name)
                cursor.execute(
                    '''\
                    INSERT INTO windows(start, end, active, name)
                    VALUES(datetime(), datetime(), ?, ?);
                    ''',
                    (active, name),
                )
                current_windows[window_id] = cursor.lastrowid, (name, active)

        logger.info('')
        database.commit()


def parse_number(s):
    if s.startswith('0x'):
        return int(s[2:], 16)
    else:
        return int(s, 10)


def get_active_window():
    output = subprocess.check_output(['xdotool', 'getactivewindow'])
    return parse_number(output.decode('utf-8').strip())


def get_windows():
    output = subprocess.check_output(['xprop', '-root'])
    output = output.decode('utf-8')
    for line in output.splitlines():
        if line.startswith('_NET_CLIENT_LIST_STACKING(WINDOW)'):
            pos = line.find('0x')
            ids = line[pos:].split(',')
            ids = [parse_number(id.strip()) for id in ids]
            return ids

    raise RuntimeError("xprop didn't provide active windows")


def get_window_name(window_id):
    output = subprocess.check_output(['xdotool', 'getwindowname', str(window_id)])
    return output.decode('utf-8').rstrip('\r\n')
