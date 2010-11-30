import unittest

from .util import SqlTestCase, main

from orm.model import *


class TestColumn(SqlTestCase):
    def test_sql(self):
        self.assertSqlEqual(Column('some_column'), '"some_column"')


class SomeModel(Model):
    orm_table = 'some_table'
    column = Column('some_column')


class TestBoundColumn(SqlTestCase):
    def test_sql(self):
        column = Column('some_column')
        model = SomeModel()
        bound = BoundColumn(column, model)
        self.assertSqlEqual(bound, '"some_table"."some_column"')

    def test_get(self):
        model = SomeModel()
        self.assertTrue(isinstance(model.column, BoundColumn))
        self.assertSqlEqual(model.column, '"some_table"."some_column"')


class TestModel(SqlTestCase):
    def test_find(self):
        self.assertSqlEqual(
            SomeModel.find(),
            'select * from "some_table"'
        )
        self.assertSqlEqual(
            SomeModel.find(SomeModel.column == 1),
            'select * from "some_table" where "some_table"."some_column" = ?',
            (1,)
        )
        self.assertSqlEqual(
            SomeModel.find(Expr(1) > 2, Expr(3) > 4),
            'select * from "some_table" where (? > ?) and (? > ?)',
            (1, 2, 3, 4)
        )


if __name__ == "__main__":
    main(__name__)
