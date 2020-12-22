from datetime import datetime, timedelta
import logging
import os
import sqlite3
import time

from .base import PynputMonitor, RecordError
from .lock import PidFile
from .utils import datetime2db
from .x11 import get_windows


logger = logging.getLogger(__name__)


MAX_INACTIVE_TIME = 30

INTERVAL = 5


def main():
    # Set up logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    # Lock pid file
    pid_file = PidFile('database.pid')

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
    input_monitor = PynputMonitor()

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
        time.sleep(INTERVAL)
        now = datetime.utcnow()

        # Check whether user has gone away
        inactive = None
        inactive_time = (now - input_monitor.last_input)
        inactive_time = inactive_time.total_seconds()
        if inactive_time > MAX_INACTIVE_TIME:
            inactive = 'inactive'

        # Check if windows can be captured
        windows = None  # avoids warning
        if not inactive:
            try:
                windows = get_windows()
            except RecordError:
                inactive = 'locked'

        if inactive:
            # He's gone
            if current_run is not None:
                logger.warning("Input inactive")

                # TODO: Erase events since he went away?

                # End run
                database.execute(
                    '''\
                    UPDATE runs
                    SET end=:now, end_reason = :reason
                    WHERE id=:id;
                    ''',
                    dict(
                        now=datetime2db(now),
                        id=current_run,
                        reason=inactive,
                    ),
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
                    VALUES(?);
                    ''',
                    (datetime2db(now),),
                )
                current_run = cursor.lastrowid
                database.commit()

        extend_windows = []
        insert_windows = []
        for window in windows:
            if window.id in current_windows:
                current = current_windows[window.id]
                if current[1] == (window.name, window.active):
                    extend_windows.append(current[0])
                else:
                    del current_windows[window.id]
                    insert_windows.append(window)
            else:
                insert_windows.append(window)

        window_ids = set(window.id for window in windows)
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
                SET end=?
                WHERE id=?;
                ''',
                ((datetime2db(now), i) for i in extend_windows),
            )
        if insert_windows:
            for window in insert_windows:
                logger.info("insert %s %s", ('Y' if window.active else 'n'), window.name)
                cursor.execute(
                    '''\
                    INSERT INTO windows(start, end, active, name)
                    VALUES(:start, :end, :active, :name);
                    ''',
                    dict(
                        start=datetime2db(now - timedelta(seconds=INTERVAL)),
                        end=datetime2db(now),
                        active=window.active,
                        name=window.name,
                    ),
                )
                current_windows[window.id] = cursor.lastrowid, (window.name, window.active)

        logger.info('')
        database.commit()
