import unittest

from ..util import *

import orm.connection


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
        class MyModel(orm.model.Model):
            orm_table = 'test_table'
            column1 = orm.model.Column()
            column2 = orm.model.Column()
        obj = MyModel.find(MyModel.column1 == 'row1_1')[0]
        self.assertTrue(isinstance(obj, MyModel))
        self.assertColumnEqual(obj.column1, 'row1_1')
        self.assertColumnEqual(obj.column2, 'row1_2')


if __name__ == "__main__":
    main(__name__)
