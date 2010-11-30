import unittest

from ..util import SqlTestCase, main

from orm.query import *


class TestQueries(SqlTestCase):
    def test_queries(self):
        self.assertSqlEqual(
            Select(Expr(1) & Expr(2) - ~Sql('current_timestamp')),
            'select ? and (? - (not current_timestamp))',
            (1, 2)
        )
        self.assertSqlEqual(
            Select(
                Sql('some_column'),
                Sql('some_table'),
                (Sql('some_column') / 2 == 3) & ~Sql('other_column'),
                Desc(Sql('order_column')),
                Limit(slice(3, 5))
            ),
            'select some_column '
            'from some_table '
            'where ((some_column / ?) = ?) and (not other_column) '
            'order by order_column desc '
            'limit 3, 2',
            (2, 3)
        )

    def test_binary_op_binding(self):
        self.assertSqlEqual(
            Select((Expr(1) & 2) - Sql('current_timestamp')),
            'select (? and ?) - current_timestamp',
            (1, 2)
        )

    def test_parenthesizing(self):
        self.assertSqlEqual(
            ~ExprList([1]),
            'not (?)',
            (1,)
        )
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
    main(__name__)
