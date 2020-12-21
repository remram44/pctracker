from datetime import datetime


def datetime2db(dt):
    return dt.strftime('%Y-%m-%d %H:%M:%S')


def db2datetime(s):
    return datetime.fromisoformat(s)
