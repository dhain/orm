import sys
import unittest

from .util import *
from .fakes import sqlite3

from orm import connection

from orm.query import *
from orm.model import *


class SomeModel(Model):
    orm_table = 'some_table'
    column1 = Column('some_column', primary=True)
    column2 = Column('other_column')

# column1, column2
SomeModel.orm_columns.sort(key=lambda x: x.attr)


class SomeModelNoPrimaries(SomeModel):
    pass

SomeModelNoPrimaries.orm_primaries = ExprList()


class SomeSubclass(SomeModel):
    column3 = Column('third_column', primary=True)


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
        attrs = 'name attr model primary'.split()
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

    def test_del(self):
        class A(object):
            col = Column()
            def __init__(self):
                self.orm_dirty = {}
        a = A()
        a.col = 1
        def del_col():
            del a.col
        self.assertRaises(
            AttributeError,
            del_col
        )


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

    def test_set(self):
        connection.connect(':memory:')
        a1 = SomeModel.as_alias('m1')
        a2 = SomeModel.as_alias('m2')
        a1.a2 = ToOne(a1.column1, a2.column1)
        connection.connection.rows = rows = [
            ('row1_1', 'row1_2'),
        ]
        obj1 = a1.find()[0]
        connection.connection.rows = rows = [
            ('row2_1', 'row2_2'),
        ]
        obj2 = a2.find()[0]
        obj1.a2 = obj2
        self.assertColumnEqual(obj1.column1, 'row2_1')

    def test_del(self):
        connection.connect(':memory:')
        connection.connection.rows = rows = [
            ('row1_1', 'row1_2'),
        ]
        a = SomeModel.as_alias('m')
        a.a = ToOne(a.column1, a.column1)
        obj = a.find()[0]
        def del_col():
            del obj.a
        self.assertRaises(
            AttributeError,
            del_col
        )

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

    def test_dereference_other_column_set(self):
        connection.connect(':memory:')
        connection.connection.rows = rows = [
            ('row1_1', 'row1_2'),
        ]
        class MyModel(Model):
            orm_table = 'my_table'
            my_id = Column()
            some_model = ToOne(my_id, 'SomeModel.column1')
        obj = MyModel()
        obj.some_model = SomeModel()
        other_column = obj.__class__.__dict__['some_model'].other_column
        self.assertTrue(other_column is SomeModel.column1)


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

    def test_set(self):
        connection.connect(':memory:')
        connection.connection.rows = rows = [
            ('row1_1', 'row1_2'),
        ]
        a = SomeModel.as_alias('m')
        a.a = ToMany(a.column1, a.column1)
        obj = a()
        def set_col():
            obj.a = []
        self.assertRaises(
            AttributeError,
            set_col
        )

    def test_del(self):
        connection.connect(':memory:')
        connection.connection.rows = rows = [
            ('row1_1', 'row1_2'),
        ]
        a = SomeModel.as_alias('m')
        a.a = ToMany(a.column1, a.column1)
        obj = a()
        def del_col():
            del obj.a
        self.assertRaises(
            AttributeError,
            del_col
        )

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

    def test_set(self):
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
        obj = a1()
        def set_col():
            obj.a2 = []
        self.assertRaises(
            AttributeError,
            set_col
        )

    def test_del(self):
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
        obj = a1()
        def del_col():
            del obj.a2
        self.assertRaises(
            AttributeError,
            del_col
        )

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

    def test_orm_primaries(self):
        self.assertTrue(isinstance(SomeModel.orm_primaries, ExprList))
        self.assertItemsIdentical(
            SomeModel.orm_primaries,
            (SomeModel.column1,)
        )

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
            'select "some_table"."some_column", "some_table"."other_column", '
            '"some_table"."oid" '
            'from "some_table"'
        )
        self.assertSqlEqual(
            SomeModel.find(SomeModel.column1 == 1),
            'select "some_table"."some_column", "some_table"."other_column", '
            '"some_table"."oid" '
            'from "some_table" where "some_table"."some_column" = ?',
            (1,)
        )
        self.assertSqlEqual(
            SomeModel.find(Expr(1) > 2, Expr(3) > 4),
            'select "some_table"."some_column", "some_table"."other_column", '
            '"some_table"."oid" '
            'from "some_table" where (? > ?) and (? > ?)',
            (1, 2, 3, 4)
        )

    def test_alias(self):
        a = SomeModel.as_alias('m')
        self.assertTrue(issubclass(a, SomeModel))
        self.assertSqlEqual(
            a.find(),
            'select "m"."some_column", "m"."other_column", "m"."oid" '
            'from "some_table" "m"'
        )
        self.assertTrue(REGISTERED_MODELS['SomeModel'] is SomeModel)
        self.assertTrue(REGISTERED_MODELS['SomeModel_as_m'] is a)


class TestModelSubclass(SqlTestCase):
    def test_orm_columns(self):
        self.assertTrue(isinstance(SomeSubclass.orm_columns, ExprList))
        self.assertItemsIdentical(
            SomeSubclass.orm_columns,
            (
                SomeSubclass.column1,
                SomeSubclass.column2,
                SomeSubclass.oid,
                SomeSubclass.column3
            )
        )
        self.assertEqual(SomeSubclass.column1.attr, 'column1')
        self.assertEqual(SomeSubclass.column1.model, SomeSubclass)

    def test_orm_primaries(self):
        self.assertTrue(isinstance(SomeSubclass.orm_primaries, ExprList))
        print SomeSubclass.orm_primaries
        self.assertItemsIdentical(
            SomeSubclass.orm_primaries,
            (SomeSubclass.column1, SomeSubclass.column3)
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
                'where "some_table"."some_column" = ?',
                ('hello', 'world', 'old1')
            ),
        ])

    def test_save_update_no_primaries(self):
        db = connection.connect(':memory:')
        obj = SomeModelNoPrimaries()
        obj.orm_new = False
        obj.__dict__['oid'] = 2
        obj.column1 = 'hello'
        obj.column2 = 'world'
        obj.save()
        self.assertFalse(obj.orm_new)
        self.assertEqual(obj.orm_dirty, {})
        self.assertEqual(db.statements, [
            (
                'update "some_table" set '
                '"some_column" = ?, "other_column" = ? '
                'where "some_table"."oid" = ?',
                ('hello', 'world', 2)
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

    def test_delete_new(self):
        db = connection.connect(':memory:')
        obj = SomeModel()
        obj.delete()
        self.assertTrue(obj.orm_new)
        self.assertEqual(obj.orm_dirty, {})
        self.assertEqual(db.statements, [])

    def test_delete(self):
        db = connection.connect(':memory:')
        obj = SomeModel()
        obj.orm_new = False
        obj.__dict__['column1'] = 'old1'
        obj.delete()
        self.assertTrue(obj.orm_new)
        self.assertEqual(obj.orm_dirty, {SomeModel.column1: 'old1'})
        self.assertEqual(db.statements, [
            (
                'delete from "some_table" '
                'where "some_table"."some_column" = ?',
                ('old1',)
            ),
        ])

    def test_delete_no_primaries(self):
        db = connection.connect(':memory:')
        obj = SomeModelNoPrimaries()
        obj.orm_new = False
        obj.__dict__['oid'] = 2
        obj.delete()
        self.assertTrue(obj.orm_new)
        self.assertEqual(obj.orm_dirty, {SomeModelNoPrimaries.oid: 2})
        self.assertEqual(db.statements, [
            (
                'delete from "some_table" '
                'where "some_table"."oid" = ?',
                (2,)
            ),
        ])


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
            ('row1_1', 'row1_2', 1, 'row1_1', 'row1_2', 1),
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
