import unittest


class SqlTestCase(unittest.TestCase):
    def assertSqlEqual(self, query, sql, args=()):
        self.assertEqual(query.sql(), sql)
        self.assertEqual(query.args(), args)
