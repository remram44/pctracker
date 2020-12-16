import logging
import os
import sqlite3
import subprocess
import time


logger = logging.getLogger(__name__)


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
                end DATETIME NULL
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
                SET end = start
                WHERE end IS NULL;
                ''',
            )
        else:
            database.execute(
                '''\
                UPDATE runs
                SET end = ?
                WHERE end IS NULL;
                ''',
                most_recent_events[0],
            )

    # Start run
    database.execute(
        '''\
        INSERT INTO runs(start)
        VALUES(datetime());
        ''',
    )
    database.commit()

    current_windows = {}

    # Loop forever
    while True:
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

        time.sleep(5)


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
