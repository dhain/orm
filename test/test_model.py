import sys
import unittest

from .util import *
from .fakes import sqlite3

from orm import connection

from orm.query import *
from orm.model import *


class SomeModel(Model):
    orm_table = 'some_table'
    column1 = Column('some_column')
    column2 = Column('other_column')

# column1, column2
SomeModel.orm_columns = tuple(sorted(
    SomeModel.orm_columns, key=lambda x: x.attr))


class TestColumn(SqlTestCase):
    def test_sql(self):
        column = Column('some_column')
        self.assertSqlEqual(column, '"some_column"')
        column = Column()
        self.assertRaises(
            TypeError,
            column.sql
        )
        column.name = 'some_column'
        self.assertSqlEqual(column, '"some_column"')
        column.model = SomeModel
        self.assertSqlEqual(column, '"some_table"."some_column"')

    def test_copy(self):
        attrs = 'name attr model'.split()
        column1 = Column()
        for attr in attrs:
            setattr(column1, attr, object())
        column2 = column1.__copy__()
        self.assertFalse(column2 is column1)
        for attr in attrs:
            self.assertEqual(getattr(column2, attr), getattr(column1, attr))


class TestModel(SqlTestCase):
    def test_orm_columns(self):
        self.assertEqual(
            set(SomeModel.orm_columns),
            set((SomeModel.column1, SomeModel.column2))
        )
        self.assertEqual(SomeModel.column1.attr, 'column1')
        self.assertEqual(SomeModel.column1.model, SomeModel)

    def test_sql(self):
        self.assertSqlEqual(
            SomeModel,
            '"some_table"'
        )

    def test_exprlist(self):
        self.assertSqlEqual(
            ExprList([SomeModel, SomeModel]),
            '"some_table", "some_table"'
        )

    def test_find(self):
        self.assertTrue(isinstance(SomeModel.find(), ModelSelect))
        self.assertSqlEqual(
            SomeModel.find(),
            'select "some_table"."some_column", "some_table"."other_column" '
            'from "some_table"'
        )
        self.assertSqlEqual(
            SomeModel.find(SomeModel.column1 == 1),
            'select "some_table"."some_column", "some_table"."other_column" '
            'from "some_table" where "some_table"."some_column" = ?',
            (1,)
        )
        self.assertSqlEqual(
            SomeModel.find(Expr(1) > 2, Expr(3) > 4),
            'select "some_table"."some_column", "some_table"."other_column" '
            'from "some_table" where (? > ?) and (? > ?)',
            (1, 2, 3, 4)
        )


class TestModelSelect(SqlTestCase):
    def setUp(self):
        connection.sqlite3 = sqlite3
        sqlite3.reset()
        connection.reset()

    def tearDown(self):
        connection.sqlite3 = sys.modules['sqlite3']

    def test_iter(self):
        connection.connect(':memory:')
        connection.connection.rows = rows = [
            ('row1_1', 'row1_2'),
            ('row2_1', 'row2_2'),
        ]
        q = SomeModel.find()
        self.assertTrue(isinstance(q, ModelSelect))
        for row, obj in zip(rows, q):
            self.assertTrue(isinstance(obj, SomeModel))
            self.assertEqual(obj.column1, row[0])
            self.assertEqual(obj.column2, row[1])


if __name__ == "__main__":
    main(__name__)
