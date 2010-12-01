import sqlite3


def reset():
    global connection
    connection = None

reset()


def connect(path):
    global connection
    connection = sqlite3.connect(path)
    return connection


def get_connection():
    global connection
    if connection is None:
        raise RuntimeError('not connected')
    return connection
