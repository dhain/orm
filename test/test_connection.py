import sys
import unittest

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


if __name__ == "__main__":
    main(__name__)
