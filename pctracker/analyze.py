import sqlite3

from .utils import db2datetime


def format_duration(seconds):
    seconds = int(seconds)
    out = '%ds' % (seconds % 60)
    if seconds >= 60:
        out = '%dm%s' % ((seconds // 60) % 60, out)
        if seconds >= 3600:
            out = '%dh%s' % (seconds // 3600, out)
    return out


class Record(object):
    def __init__(self, start, end, name):
        self.start = db2datetime(start)
        self.end = db2datetime(end)
        self.fullname = name
        self.name = name

    @property
    def duration(self):
        return (self.end - self.start).total_seconds()


class OutputNode(object):
    def __init__(self, name):
        self.name = name
        self.duration = 0
        self.children = {}

    def child(self, name):
        try:
            child = self.children[name]
        except KeyError:
            child = self.children[name] = OutputNode(name)
        return child

    def print(self, indent=0):
        if indent == 0:
            prefix = ''
            last_prefix = '└── '
        else:
            prefix = '│   ' * (indent - 1)
            prefix += '├── '
            last_prefix = '|   ' * indent
            last_prefix += '└── '
        name = self.name or 'total'
        other_duration = self.duration
        duration = format_duration(self.duration)
        print(f'{prefix}{name} {duration}')
        children = sorted(self.children.values(), key=lambda c: -c.duration)
        for child in children:
            child.print(indent + 1)
            other_duration -= child.duration
        if self.children:
            print(f'{last_prefix}other {other_duration}')


def prefix(string, name=None):
    def prefix_matcher(record):
        if record.name.startswith(string):
            return record.name[len(string):]
        else:
            return None

    if not name:
        name = repr(string)

    return name, prefix_matcher


def suffix(string, name=None):
    def suffix_matcher(record):
        if record.name.endswith(string):
            return record.name[:-len(string)]
        else:
            return None

    if not name:
        name = repr(string)

    return name, suffix_matcher


def apply_filters(record, filters, output):
    # Add duration to current node
    output.duration += record.duration
    # Apply filters until one matches
    for (name, matcher), then_ops in filters:
        m = matcher(record)
        if m is not None:
            record.name = m
            apply_filters(record, then_ops, output.child(name))
            return


def main():
    # Open database
    database = sqlite3.connect('database.sqlite3')

    # Create output tree
    output = OutputNode(None)

    # Rules, hard-coded for now
    filters = [
        (suffix(' — Mozilla Firefox', 'Firefox'), [
            (suffix(' - YouTube', 'YouTube'), []),
            (suffix(' Hacker News', 'HackerNews'), []),
            (suffix(' GitLab', 'GitLab'), []),
            (suffix(' - Gmail', 'Gmail'), []),
            (prefix('Slack', 'Slack'), []),
            (suffix(' - Jupyter Notebook', 'Jupyter'), []),
        ]),
        (suffix(' - Google Chrome', 'Google Chrome'), []),
        (prefix('Signal', 'Signal'), []),
        (suffix(' - GVIM', 'GVIM'), []),
        (suffix(' — Konsole', 'Konsole'), []),
    ]

    # Process records
    for row in database.execute('''\
        SELECT start, end, name
        FROM windows
        WHERE active=1;
    '''):
        record = Record(*row)
        apply_filters(record, filters, output)

    output.print()
