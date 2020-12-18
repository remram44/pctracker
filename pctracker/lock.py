import contextlib
import os


class Locked(Exception):
    """File is already locked"""


try:
    import fcntl
except ImportError:
    import msvcrt  # Might raise ImportError

    # Windows
    @contextlib.contextmanager
    def lock_file(file):
        try:
            msvcrt.locking(file.fileno(), msvcrt.LK_NBLCK, 1)
        except IOError:
            raise Locked
        try:
            yield
        finally:
            file.seek(0)
            msvcrt.locking(file.fileno(), msvcrt.LK_UNLCK, 1)
else:
    # Unix
    @contextlib.contextmanager
    def lock_file(file):
        try:
            fcntl.flock(file.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
        except IOError:
            raise Locked
        try:
            yield
        finally:
            fcntl.flock(file.fileno(), fcntl.LOCK_UN)


class PidFile(object):
    def __init__(self, filename):
        self.context = contextlib.ExitStack()

        # Open the file
        file = self.context.enter_context(open(filename, 'a'))

        # Lock it
        self.context.enter_context(lock_file(file))

        # Write our PID to it
        file.seek(0, 0)
        file.truncate()
        file.write('%d\n' % os.getpid())
        file.truncate()

    def close(self):
        with self.context.pop_all():
            pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
