import sqlite3
import threading


def reset():
    global state
    state = threading.local()

reset()


def connect(path):
    global state
    state.connection = connection = sqlite3.connect(path)
    return connection


def get_connection():
    global state
    try:
        return state.connection
    except AttributeError:
        raise RuntimeError('not connected')
