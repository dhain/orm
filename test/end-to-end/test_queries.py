import unittest

from ..util import SqlTestCase

from orm.query import *


class TestQueries(SqlTestCase):
    def test_queries(self):
        self.assertSqlEqual(
            Select(Expr(1) & Expr(2) - ~Sql('current_timestamp')),
            'select ? and (? - (not current_timestamp))',
            (1, 2)
        )

    def test_binary_op_binding(self):
        self.assertSqlEqual(
            Select((Expr(1) & 2) - Sql('current_timestamp')),
            'select (? and ?) - current_timestamp',
            (1, 2)
        )

    def test_select_parenthesizing(self):
        self.assertSqlEqual(
            Select(1) + 2,
            '(select ?) + ?',
            (1, 2)
        )

    def test_isin_select(self):
        self.assertSqlEqual(
            Expr(1).isin(Select(2)),
            '? in (select ?)',
            (1, 2)
        )


if __name__ == "__main__":
    import sys
    tests = unittest.defaultTestLoader.loadTestsFromModule(
        sys.modules[__name__])
    test_suite = unittest.TestSuite(tests)
    unittest.TextTestRunner(verbosity=2).run(test_suite)
