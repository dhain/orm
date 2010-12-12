import unittest

from ..util import *

import orm.connection


class SomeModel(orm.model.Model):
    orm_table = 'test_table'
    column1 = orm.model.Column()
    column2 = orm.model.Column()


class OtherModel(orm.model.Model):
    orm_table = 'other_table'
    some_model_id = orm.model.Column('some_model')
    some_model = orm.model.ToOne(some_model_id, SomeModel.column1)
    column1 = orm.model.Column()


class TestOrm(SqlTestCase):
    def setUp(self):
        self.db = orm.connection.connect(':memory:')
        cur = self.db.cursor()
        with self.db:
            cur.executescript(
                '''
                create table test_table (
                    column1 text,
                    column2 text
                );
                insert into test_table (column1, column2)
                    values ('row1_1', 'row1_2');
                insert into test_table (column1, column2)
                    values ('row2_1', 'row2_2');

                create table other_table (
                    some_model text,
                    column1 text
                );
                insert into other_table (some_model, column1)
                    values ('row1_1', 'myrow1_1');
                insert into other_table (some_model, column1)
                    values ('row2_1', 'myrow2_1');
                '''
            )

    def test_select_iter(self):
        q = orm.query.Select(sources=orm.query.Sql('test_table'))
        self.assertEqual(
            list(q),
            [
                ('row1_1', 'row1_2'),
                ('row2_1', 'row2_2'),
            ]
        )

    def test_select_getitem_slice(self):
        q = orm.query.Select(sources=orm.query.Sql('test_table'))
        self.assertEqual(
            list(q[:1]),
            [
                ('row1_1', 'row1_2'),
            ]
        )

    def test_select_getitem_index(self):
        q = orm.query.Select(sources=orm.query.Sql('test_table'))
        self.assertEqual(q[1], ('row2_1', 'row2_2'))
        self.assertEqual(q[0], ('row1_1', 'row1_2'))

    def test_select_getitem_index_indexerror(self):
        q = orm.query.Select(sources=orm.query.Sql('test_table'))
        self.assertRaises(IndexError, q.__getitem__, 2)

    def test_model(self):
        obj = SomeModel.find(SomeModel.column1 == 'row1_1')[0]
        self.assertTrue(isinstance(obj, SomeModel))
        self.assertColumnEqual(obj.column1, 'row1_1')
        self.assertColumnEqual(obj.column2, 'row1_2')

    def test_model_subclass(self):
        class NullColumn(orm.model.Column):
            def sql(self):
                return '1'
        class MyModel(SomeModel):
            column3 = NullColumn()
        obj = MyModel.find(MyModel.column1 == 'row1_1')[0]
        self.assertTrue(isinstance(obj, MyModel))
        self.assertColumnEqual(obj.column1, 'row1_1')
        self.assertColumnEqual(obj.column2, 'row1_2')
        self.assertColumnEqual(obj.column3, 1)

    def test_join(self):
        a1 = SomeModel.as_alias('m1')
        a2 = SomeModel.as_alias('m2')
        obj1, obj2 = orm.model.ModelSelect(
            a1.orm_columns + a2.orm_columns,
            orm.query.ExprList([a1, a2]),
            a1.column1 == a2.column1
        ).order_by(a1.column1)[0]
        for obj in (obj1, obj2):
            self.assertTrue(isinstance(obj, SomeModel))
            self.assertColumnEqual(obj.column1, 'row1_1')
            self.assertColumnEqual(obj.column2, 'row1_2')

    def test_to_one(self):
        obj = OtherModel.find(OtherModel.column1 == 'myrow1_1')[0]
        other = obj.some_model
        self.assertTrue(isinstance(other, SomeModel))
        self.assertColumnEqual(other.column1, 'row1_1')

    def test_to_one_not_found(self):
        obj = OtherModel.find(OtherModel.column1 == 'myrow1_1')[0]
        obj.some_model_id = 'bogus_value'
        other = obj.some_model
        self.assertTrue(other is None)


if __name__ == "__main__":
    main(__name__)
