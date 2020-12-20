import math
import unittest


class TrieCounter(object):
    def __init__(self):
        self.cardinality = 0
        self.elements = {}

    def add(self, iterable):
        self._add(iter(iterable))

    def _add(self, iterator):
        self.cardinality += 1

        try:
            element = next(iterator)
        except StopIteration:
            return

        try:
            node = self.elements[element]
        except KeyError:
            node = self.elements[element] = TrieCounter()
        node._add(iterator)

    def _most_common(self, threshold, first=False):
        yielded = 0
        for key, node in sorted(
            self.elements.items(),
            key=lambda p: -p[1].cardinality,
        ):
            if node.cardinality < threshold:
                break
            for seq, card in node._most_common(threshold):
                yielded += card
                yield (key,) + seq, card
        if not first and self.cardinality - yielded > threshold:
            yield (), self.cardinality

    def most_common(self, threshold=0.2):
        if threshold < 1:
            threshold = math.floor(threshold * self.cardinality)
        if self.cardinality < threshold:
            return
        return self._most_common(threshold, True)

    def __eq__(self, other):
        if not isinstance(other, TrieCounter):
            return False
        return (
            self.cardinality == other.cardinality
            and self.elements == other.elements
        )

    def __repr__(self):
        if self.elements:
            return 't(%d, %s)' % (
                self.cardinality,
                ', '.join('%s=%r' % (k, v)
                          for k, v in sorted(self.elements.items()))
            )
        else:
            return 't(%d)' % self.cardinality


class TestTrieCounter(unittest.TestCase):
    def test_trie(self):
        trie = TrieCounter()
        trie.add('abc')
        trie.add('abde')
        trie.add('cde')
        trie.add('cfg')
        trie.add('abdij')
        trie.add('dfg')
        trie.add('af')

        def t(card, **e):
            tr = TrieCounter()
            tr.cardinality = card
            tr.elements = e
            return tr

        self.assertEqual(
            trie,
            t(
                7,
                a=t(
                    4,
                    b=t(
                        3,
                        c=t(1),
                        d=t(
                            2,
                            e=t(1),
                            i=t(
                                1,
                                j=t(1),
                            ),
                        ),
                    ),
                    f=t(1),
                ),
                c=t(
                    2,
                    d=t(
                        1,
                        e=t(1),
                    ),
                    f=t(
                        1,
                        g=t(1),
                    ),
                ),
                d=t(
                    1,
                    f=t(
                        1,
                        g=t(1),
                    ),
                )
            ),
        )

    def test_most_common(self):
        trie = TrieCounter()
        trie.add('abc')
        trie.add('abde')
        trie.add('cde')
        trie.add('cfg')
        trie.add('abdij')
        trie.add('dfg')
        trie.add('af')

        self.assertEqual(
            list(trie.most_common()),
            [
                (('a', 'b', 'd'), 2),
                (('a',), 4),
                (('c',), 2),
            ],
        )


if __name__ == '__main__':
    unittest.main()
