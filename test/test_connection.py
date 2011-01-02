import sys
import unittest
import threading

from .util import *
from .fakes import sqlite3

from orm import connection


class TestConnection(unittest.TestCase):
    def setUp(self):
        connection.sqlite3 = sqlite3
        sqlite3.reset()
        connection.reset()

    def tearDown(self):
        connection.sqlite3 = sys.modules['sqlite3']

    def test_connect(self):
        path = ':memory:'
        con = connection.connect(path)
        self.assertEqual([con], sqlite3.Connection.instances)
        self.assertEqual(con.path, path)

    def test_get_connection(self):
        self.assertRaises(RuntimeError, connection.get_connection)
        con = connection.connect(':memory:')
        self.assertEqual(connection.get_connection(), con)

    def test_connection_is_threadlocal(self):
        def do_it(i, res, cond1, cond2):
            with cond1:
                connection.connect(i)
                cond1.notify_all()
            # wait for all threads to connect before appending to res
            with cond1:
                while len(sqlite3.Connection.instances) < n:
                    cond1.wait()
                with cond2:
                    con = connection.get_connection()
                    res.append(con.path)
                    cond2.notify()
        cond1 = threading.Condition()
        cond2 = threading.Condition()
        res = []
        n = 3
        for i in xrange(n):
            t = threading.Thread(target=do_it, args=(i, res, cond1, cond2))
            t.start()
        with cond2:
            while len(res) < n:
                cond2.wait()
        self.assertEqual(set(res), set(xrange(3)), res)


if __name__ == "__main__":
    main(__name__)
