from datetime import datetime
import unittest


def datetime2db(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def db2datetime(s):
    return datetime.fromisoformat(s)


class PeekableIterator(object):
    class _End(object):
        def __bool__(self):
            return False

    END = _End()

    def __init__(self, iterator):
        self._iterator = iter(iterator)
        try:
            self._next = next(self._iterator)
        except StopIteration:
            self._next = self.END

    def peek(self):
        return self._next

    def __iter__(self):
        return self

    def __next__(self):
        if self._next is self.END:
            raise StopIteration
        elem = self._next
        try:
            self._next = next(self._iterator)
        except StopIteration:
            self._next = self.END
        return elem


class TestPeek(unittest.TestCase):
    def test_peek(self):
        it = PeekableIterator('abc')
        self.assertEqual(it.peek(), 'a')
        self.assertEqual(next(it), 'a')
        self.assertEqual(it.peek(), 'b')
        self.assertEqual(next(it), 'b')
        self.assertEqual(it.peek(), 'c')
        self.assertEqual(next(it), 'c')
        self.assertEqual(it.peek(), PeekableIterator.END)
        self.assertFalse(it.peek())
        self.assertRaises(StopIteration, lambda: next(it))

        it = PeekableIterator('abc')
        self.assertEqual(list(it), list('abc'))


if __name__ == '__main__':
    unittest.main()
