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
SomeModel.orm_columns.sort(key=lambda x: x.attr)


class SomeModelSomeModel(Model):
    orm_table = 'some_table_some_table'
    m1_column1 = Column()
    m2_column1 = Column()


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

    def test_set(self):
        class A(object):
            def __init__(self):
                self.orm_dirty = {}
        a = A()
        col = Column()
        col.attr = 'x'
        col.__set__(a, 1)
        self.assertEqual(a.x, 1)
        self.assertEqual(a.orm_dirty, {col: Column.no_value})


class TestDereferenceColumn(SqlTestCase):
    def test_dereference_column(self):
        column = dereference_column('SomeModel.column1')
        self.assertTrue(column is SomeModel.column1)

    def test_dereference_column_unregistered_model(self):
        self.assertRaises(
            RuntimeError,
            dereference_column,
            'BogusModel.column'
        )

    def test_dereference_column_undefined_column(self):
        self.assertRaises(
            RuntimeError,
            dereference_column,
            'SomeModel.bogus_column'
        )


class TestToOne(SqlTestCase):
    def setUp(self):
        connection.sqlite3 = sqlite3
        sqlite3.reset()
        connection.reset()

    def tearDown(self):
        connection.sqlite3 = sys.modules['sqlite3']

    def test_get(self):
        connection.connect(':memory:')
        connection.connection.rows = rows = [
            ('row1_1', 'row1_2'),
        ]
        a1 = SomeModel.as_alias('m1')
        a2 = SomeModel.as_alias('m2')
        a1.a2 = t = ToOne(a1.column1, a2.column1)
        self.assertTrue(a1.a2 is t)
        obj = a1.find(a1.column1 == 'row1_1')[0].a2
        self.assertTrue(isinstance(obj, a2))

    def test_get_not_found(self):
        connection.connect(':memory:')
        connection.connection.rows = rows = [
            ('row1_1', 'row1_2'),
        ]
        a1 = SomeModel.as_alias('m1')
        a2 = SomeModel.as_alias('m2')
        a1.a2 = ToOne(a1.column1, a2.column1)
        a1_obj = a1.find(a1.column1 == 'row1_1')[0]
        connection.connection.rows = rows = []
        a2_obj = a1_obj.a2
        self.assertTrue(a2_obj is None)

    def test_dereference_other_column(self):
        connection.connect(':memory:')
        connection.connection.rows = rows = [
            ('row1_1', 'row1_2'),
        ]
        class MyModel(Model):
            orm_table = 'my_table'
            my_id = Column()
            some_model = ToOne(my_id, 'SomeModel.column1')
        obj = MyModel()
        self.assertTrue(isinstance(obj.some_model, SomeModel))


class TestToMany(SqlTestCase):
    def setUp(self):
        connection.sqlite3 = sqlite3
        sqlite3.reset()
        connection.reset()

    def tearDown(self):
        connection.sqlite3 = sys.modules['sqlite3']

    def test_get(self):
        connection.connect(':memory:')
        connection.connection.rows = rows = [
            ('row1_1', 'row1_2'),
        ]
        a1 = SomeModel.as_alias('m1')
        a2 = SomeModel.as_alias('m2')
        a1.a2 = t = ToMany(a1.column1, a2.column1)
        self.assertTrue(a1.a2 is t)
        obj = a1.find(a1.column1 == 'row1_1')[0]
        res = obj.a2
        self.assertTrue(isinstance(res, ModelSelect))
        self.assertTrue(isinstance(res[0], a2))

    def test_dereference_other_column(self):
        connection.connect(':memory:')
        connection.connection.rows = rows = [
            ('row1_1', 'row1_2'),
        ]
        class MyModel(Model):
            orm_table = 'my_table'
            my_id = Column()
            some_models = ToMany(my_id, 'SomeModel.column1')
        obj = MyModel()
        self.assertTrue(isinstance(obj.some_models[0], SomeModel))


class TestManyToMany(SqlTestCase):
    def setUp(self):
        connection.sqlite3 = sqlite3
        sqlite3.reset()
        connection.reset()

    def tearDown(self):
        connection.sqlite3 = sys.modules['sqlite3']

    def test_get(self):
        connection.connect(':memory:')
        connection.connection.rows = rows = [
            ('row1_1', 'row1_2'),
        ]
        a1 = SomeModel.as_alias('m1')
        a2 = SomeModel.as_alias('m2')
        a1.a2 = t = ManyToMany(
            a1.column1, SomeModelSomeModel.m1_column1,
            SomeModelSomeModel.m2_column1, a2.column1
        )
        self.assertTrue(a1.a2 is t)
        obj = a1.find(a1.column1 == 'row1_1')[0]
        res = obj.a2
        self.assertTrue(isinstance(res, ModelSelect))
        self.assertTrue(isinstance(res[0], a2))

    def test_dereference_my_join(self):
        connection.connect(':memory:')
        connection.connection.rows = rows = [
            ('row1_1', 'row1_2'),
        ]
        class MyModel(Model):
            orm_table = 'my_table'
            my_id = Column()
            some_models = ManyToMany(
                my_id, 'SomeModelSomeModel.m1_column1',
                SomeModelSomeModel.m2_column1, SomeModel.column1
            )
        obj = MyModel()
        self.assertTrue(isinstance(obj.some_models[0], SomeModel))

    def test_dereference_other_join(self):
        connection.connect(':memory:')
        connection.connection.rows = rows = [
            ('row1_1', 'row1_2'),
        ]
        class MyModel(Model):
            orm_table = 'my_table'
            my_id = Column()
            some_models = ManyToMany(
                my_id, SomeModelSomeModel.m1_column1,
                'SomeModelSomeModel.m2_column1', SomeModel.column1
            )
        obj = MyModel()
        self.assertTrue(isinstance(obj.some_models[0], SomeModel))

    def test_dereference_other_column(self):
        connection.connect(':memory:')
        connection.connection.rows = rows = [
            ('row1_1', 'row1_2'),
        ]
        class MyModel(Model):
            orm_table = 'my_table'
            my_id = Column()
            some_models = ManyToMany(
                my_id, SomeModelSomeModel.m1_column1,
                SomeModelSomeModel.m2_column1, 'SomeModel.column1'
            )
        obj = MyModel()
        self.assertTrue(isinstance(obj.some_models[0], SomeModel))


class TestModel(SqlTestCase):
    def test_orm_columns(self):
        self.assertTrue(isinstance(SomeModel.orm_columns, ExprList))
        self.assertItemsIdentical(
            SomeModel.orm_columns,
            (SomeModel.column1, SomeModel.column2)
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

    def test_alias(self):
        a = SomeModel.as_alias('m')
        self.assertTrue(issubclass(a, SomeModel))
        self.assertSqlEqual(
            a.find(),
            'select "m"."some_column", "m"."other_column" '
            'from "some_table" "m"'
        )


class TestModelActions(SqlTestCase):
    def setUp(self):
        connection.sqlite3 = sqlite3
        sqlite3.reset()
        connection.reset()

    def tearDown(self):
        connection.sqlite3 = sys.modules['sqlite3']

    def test_save_insert(self):
        db = connection.connect(':memory:')
        obj = SomeModel()
        obj.column1 = 'hello'
        obj.column2 = 'world'
        obj.save()
        self.assertFalse(obj.orm_new)
        self.assertEqual(obj.orm_dirty, {})
        self.assertEqual(db.statements, [
            (
                'insert into "some_table" '
                '("some_column", "other_column") values (?, ?)',
                ('hello', 'world')
            ),
        ])

    def test_save_insert_default_values(self):
        db = connection.connect(':memory:')
        obj = SomeModel()
        obj.save()
        self.assertFalse(obj.orm_new)
        self.assertEqual(obj.orm_dirty, {})
        self.assertEqual(db.statements, [
            ('insert into "some_table" default values', ()),
        ])

    def test_save_update(self):
        db = connection.connect(':memory:')
        obj = SomeModel()
        obj.orm_new = False
        obj.__dict__['column1'] = 'old1'
        obj.__dict__['column2'] = 'old2'
        obj.column1 = 'hello'
        obj.column2 = 'world'
        obj.save()
        self.assertFalse(obj.orm_new)
        self.assertEqual(obj.orm_dirty, {})
        self.assertEqual(db.statements, [
            (
                'update "some_table" set '
                '"some_column" = ?, "other_column" = ? '
                'where ("some_table"."some_column" = ?) '
                'and ("some_table"."other_column" = ?)',
                ('hello', 'world', 'old1', 'old2')
            ),
        ])

    def test_save_update_no_dirty(self):
        db = connection.connect(':memory:')
        obj = SomeModel()
        obj.orm_new = False
        obj.save()
        self.assertFalse(obj.orm_new)
        self.assertEqual(obj.orm_dirty, {})
        self.assertEqual(db.statements, [])


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
            self.assertFalse(obj.orm_new)
            self.assertEqual(obj.orm_dirty, {})
            self.assertColumnEqual(obj.column1, row[0])
            self.assertColumnEqual(obj.column2, row[1])

    def test_join(self):
        connection.connect(':memory:')
        connection.connection.rows = rows = [
            ('row1_1', 'row1_2', 'row1_1', 'row1_2'),
        ]
        a1 = SomeModel.as_alias('m1')
        a2 = SomeModel.as_alias('m2')
        obj1, obj2 = ModelSelect(
            a1.orm_columns + a2.orm_columns,
            ExprList([a1, a2])
        )[0]
        for obj in (obj1, obj2):
            self.assertTrue(isinstance(obj, SomeModel))
            self.assertColumnEqual(obj.column1, 'row1_1')
            self.assertColumnEqual(obj.column2, 'row1_2')


if __name__ == "__main__":
    main(__name__)
