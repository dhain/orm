import sys
import unittest

from .util import *
from .fakes import sqlite3

from orm import connection

from orm.query import *


binary_ops = [
    ('Eq', '=', '__eq__'),
    ('Ne', '!=', '__ne__'),
    ('Lt', '<', '__lt__'),
    ('Gt', '>', '__gt__'),
    ('Le', '<=', '__le__'),
    ('Ge', '>=', '__ge__'),
    ('And', 'and', '__and__'),
    ('Or', 'or', '__or__'),
    ('Add', '+', '__add__'),
    ('Sub', '-', '__sub__'),
    ('Mul', '*', '__mul__'),
    ('Div', '/', '__div__'),
    ('Mod', '%', '__mod__'),
    ('In', 'in', 'isin'),
    ('Like', 'like', 'like'),
    ('Glob', 'glob', 'glob'),
    ('Match', 'match', 'match'),
    ('Regexp', 'regexp', 'regexp'),
]

prefix_unary_ops = [
    ('Not', 'not', '__invert__'),
    ('Pos', '+', '__pos__'),
    ('Neg', '-', '__neg__'),
]

postfix_unary_ops = [
    ('IsNull', 'isnull', 'isnull'),
    ('NotNull', 'notnull', 'notnull'),
]


class TestExpr(SqlTestCase):
    def test_basic_value(self):
        self.assertSqlEqual(Expr(1), '?', (1,))

    def test_expr_value(self):
        self.assertSqlEqual(Expr(Expr(1)), '?', (1,))

    def test_binary_ops(self):
        expr1 = Expr(1)
        expr2 = Expr(2)
        for class_name, op, method_name in binary_ops:
            cls = globals()[class_name]
            res = getattr(expr1, method_name)(expr2)
            self.assertTrue(isinstance(res, cls))
            self.assertTrue(res.lvalue is expr1)
            self.assertTrue(res.rvalue is expr2)

    def test_unary_ops(self):
        expr = Expr(1)
        for class_name, op, method_name in (
            prefix_unary_ops + postfix_unary_ops
        ):
            cls = globals()[class_name]
            res = getattr(expr, method_name)()
            self.assertTrue(isinstance(res, cls))
            self.assertTrue(res.value is expr)

    def test_eq_null(self):
        expr = (Expr(1) == None)
        self.assertTrue(isinstance(expr, IsNull))

    def test_ne_null(self):
        expr = (Expr(1) != None)
        self.assertTrue(isinstance(expr, NotNull))


class TestExprExecute(unittest.TestCase):
    def setUp(self):
        connection.sqlite3 = sqlite3
        sqlite3.reset()
        connection.reset()

    def tearDown(self):
        connection.sqlite3 = sys.modules['sqlite3']

    def test_execute(self):
        db = connection.connect(':memory:')
        q = Expr(1) + 2
        cur = q.execute()
        self.assertEqual(db.statements, [('? + ?', (1, 2))])
        self.assertTrue(isinstance(cur, sqlite3.Cursor))

    def test_executemany(self):
        db = connection.connect(':memory:')
        q = Expr(1) + 2
        cur = q.executemany([(1, 2), (3, 4)])
        self.assertEqual(db.many_statements, [('? + ?', [(1, 2), (3, 4)])])
        self.assertTrue(isinstance(cur, sqlite3.Cursor))


class TestUnaryOps(SqlTestCase):
    def test_unary_ops(self):
        for class_name, op, method_name in prefix_unary_ops:
            cls = globals()[class_name]
            inst = cls(1)
            self.assertSqlEqual(inst, '%s ?' % (op,), (1,))
        for class_name, op, method_name in postfix_unary_ops:
            cls = globals()[class_name]
            inst = cls(1)
            self.assertSqlEqual(inst, '? %s' % (op,), (1,))

    def test_parenthesization(self):
        for class_name, op, method_name in prefix_unary_ops:
            cls = globals()[class_name]
            inst = cls(Expr(1) + Expr(2))
            self.assertSqlEqual(inst, '%s (? + ?)' % (op,), (1, 2))
        for class_name, op, method_name in postfix_unary_ops:
            cls = globals()[class_name]
            inst = cls(Expr(1) + Expr(2))
            self.assertSqlEqual(inst, '(? + ?) %s' % (op,), (1, 2))


class TestBinaryOps(SqlTestCase):
    def test_binary_ops(self):
        lvalue = 1
        rvalue = Expr(2)
        for class_name, op, method_name in binary_ops:
            cls = globals()[class_name]
            inst = cls(lvalue, rvalue)
            self.assertSqlEqual(
                inst,
                '? %s %s' % (op, rvalue.sql()),
                (lvalue,) + rvalue.args()
            )

    def test_parenthesization(self):
        for class_name, op, method_name in binary_ops:
            cls = globals()[class_name]
            inst = cls(~Expr(1), 2)
            self.assertSqlEqual(inst, '(not ?) %s ?' % (op,), (1, 2))
            inst = cls(1, ~Expr(2))
            self.assertSqlEqual(inst, '? %s (not ?)' % (op,), (1, 2))


class TestSql(SqlTestCase):
    def test_sql(self):
        sql = 'some raw sql string'
        self.assertSqlEqual(Sql(sql), sql)


class TestExprList(SqlTestCase):
    def test_exprlist(self):
        expr = ExprList(range(3))
        self.assertSqlEqual(expr, '?, ?, ?', (0, 1, 2))

    def test_append(self):
        expr = ExprList()
        self.assertSqlEqual(expr, '')
        expr.append(1)
        self.assertSqlEqual(expr, '?', (1,))
        expr.append(2)
        self.assertSqlEqual(expr, '?, ?', (1, 2))

    def test_extend(self):
        expr = ExprList()
        expr.extend(range(3))
        self.assertSqlEqual(expr, '?, ?, ?', (0, 1, 2))

    def test_insert(self):
        expr = ExprList((1, 2))
        expr.insert(0, 0)
        self.assertSqlEqual(expr, '?, ?, ?', (0, 1, 2))

    def test_getitem(self):
        expr = ExprList(range(3))
        self.assertSqlEqual(expr.__getitem__(0), '?', (0,))
        self.assertSqlEqual(expr.__getitem__(slice(1, None)), '?, ?', (1, 2))

    def test_getslice(self):
        expr = ExprList(range(3))
        self.assertSqlEqual(expr.__getslice__(1, 3), '?, ?', (1, 2))

    def test_setitem(self):
        expr = ExprList(range(3))
        expr.__setitem__(0, 4)
        self.assertSqlEqual(expr, '?, ?, ?', (4, 1, 2))
        expr.__setitem__(slice(1, None), [5, 6])
        self.assertSqlEqual(expr, '?, ?, ?', (4, 5, 6))

    def test_setslice(self):
        expr = ExprList(range(3))
        expr.__setslice__(1, 3, [3, 4])
        self.assertSqlEqual(expr, '?, ?, ?', (0, 3, 4))

    def test_add(self):
        expr = ExprList() + [1, 2, 3]
        self.assertSqlEqual(expr, '?, ?, ?', (1, 2, 3))

    def test_iadd(self):
        expr = ExprList()
        expr += [1, 2, 3]
        self.assertSqlEqual(expr, '?, ?, ?', (1, 2, 3))

    def test_mul(self):
        expr = ExprList([0])
        expr = expr * 3
        self.assertSqlEqual(expr, '?, ?, ?', (0, 0, 0))

    def test_rmul(self):
        expr = ExprList([0])
        expr = 3 * expr
        self.assertSqlEqual(expr, '?, ?, ?', (0, 0, 0))

    def test_imul(self):
        expr = ExprList([0])
        expr *= 3
        self.assertSqlEqual(expr, '?, ?, ?', (0, 0, 0))

    def test_parenthesization(self):
        expr = ExprList([~Expr(1), 2])
        self.assertSqlEqual(expr, '(not ?), ?', (1, 2))


class TestOrdering(SqlTestCase):
    def test_asc(self):
        self.assertSqlEqual(Asc(Sql('column1')), 'column1 asc')

    def test_desc(self):
        self.assertSqlEqual(Desc(Sql('column1')), 'column1 desc')


class TestLimit(SqlTestCase):
    def test_no_limit(self):
        limit = Limit(slice(None))
        self.assertSqlEqual(limit, '')

    def test_simple_number_limit(self):
        self.assertSqlEqual(Limit(3), 'limit 3')

    def test_non_number_raises_typeerror(self):
        self.assertRaises(TypeError, Limit, slice('asdf'))
        self.assertRaises(TypeError, Limit, slice('asdf', None))

    def test_step_raises_typeerror(self):
        self.assertRaises(TypeError, Limit, slice(10, 11, 2))

    def test_upper_less_than_lower_raises_valueerror(self):
        self.assertRaises(ValueError, Limit, slice(11, 9))

    def test_negative_values_raise_notimplementederror(self):
        self.assertRaises(NotImplementedError, Limit, slice(-1))
        self.assertRaises(NotImplementedError, Limit, slice(-1, None))

    def test_upper_limit(self):
        limit = Limit(slice(10))
        self.assertSqlEqual(limit, 'limit 10')

    def test_lower_limit(self):
        limit = Limit(slice(10, None))
        self.assertSqlEqual(limit, 'limit 10, -1')

    def test_upper_and_lower_limit(self):
        limit = Limit(slice(10, 11))
        self.assertSqlEqual(limit, 'limit 10, 1')
        limit = Limit(slice(9, 14))
        self.assertSqlEqual(limit, 'limit 9, 5')


class TestSelect(SqlTestCase):
    def setUp(self):
        connection.sqlite3 = sqlite3
        sqlite3.reset()
        connection.reset()

    def tearDown(self):
        connection.sqlite3 = sys.modules['sqlite3']

    def test_select(self):
        self.assertSqlEqual(
            Select(sources=Sql('some_table')),
            'select * from some_table'
        )

    def test_no_what_no_sources_raises_typeerror(self):
        self.assertRaises(TypeError, Select)

    def test_basic_value(self):
        self.assertSqlEqual(Select(1), 'select ?', (1,))

    def test_sql_value(self):
        sql = 'some raw sql string'
        self.assertSqlEqual(Select(Sql(sql)), 'select %s' % (sql,))

    def test_sources(self):
        self.assertSqlEqual(
            Select(sources=Sql('some_table')),
            'select * from some_table'
        )

    def test_where(self):
        self.assertSqlEqual(
            Select(Sql('1'), where=Sql('some_condition')),
            'select 1 where some_condition'
        )

    def test_order(self):
        self.assertSqlEqual(
            Select(Sql('1'), order=Desc(Sql('some_column'))),
            'select 1 order by some_column desc'
        )

    def test_limit(self):
        self.assertSqlEqual(
            Select(Sql('1'), limit=Limit(2)),
            'select 1 limit 2'
        )

    def test_all_clauses(self):
        q = Select(
            Sql('1'),
            Sql('some_table'),
            Sql('some_condition'),
            Desc(Sql('some_column')),
            Limit(2)
        )
        self.assertSqlEqual(
            q,
            'select 1 from some_table '
            'where some_condition order by some_column desc limit 2'
        )

    def test_combined(self):
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

    def test_isin_select(self):
        self.assertSqlEqual(
            Expr(3).isin(Select(Sql('some_column'), Sql('some_table'))),
            '? in (select some_column from some_table)',
            (3,)
        )

    def test_exists(self):
        connection.connect(':memory:')
        q = Select(sources=Sql('some_table'))
        self.assertFalse(q.exists())
        self.assertEqual(
            connection.get_connection().statements,
            [('select 1 from some_table limit 1', ())]
        )
        connection.get_connection().rows = rows = [(1,)]
        self.assertTrue(q.exists())

    def test_len(self):
        connection.connect(':memory:')
        q = Select(sources=Sql('some_table'))
        connection.get_connection().rows = [(0,)]
        self.assertEqual(len(q), 0)
        self.assertEqual(
            connection.get_connection().statements,
            [('select count(*) from some_table', ())]
        )
        connection.get_connection().rows = [(5,)]
        self.assertEqual(len(q), 5)

    def test_len_with_limit(self):
        connection.connect(':memory:')
        q = Select(sources=Sql('some_table'))
        connection.get_connection().rows = [(5,)]
        self.assertEqual(len(q[3:]), 2)
        self.assertEqual(
            connection.get_connection().statements,
            [('select count(*) from some_table', ())]
        )

    def test_iter(self):
        connection.connect(':memory:')
        connection.get_connection().rows = rows = [('col1', 'col2')]
        q = Select(sources=Sql('some_table'))
        self.assertEqual(list(q), rows)
        self.assertEqual(
            connection.get_connection().statements,
            [
                ('select * from some_table', ()),
                # in cpython, list(x) calls len(x)
                ('select count(*) from some_table', ()),
            ]
        )

    def test_getitem_slice(self):
        self.assertSqlEqual(
            Select(Sql('1'))[:2],
            'select 1 limit 2'
        )
        self.assertSqlEqual(
            Select(Sql('1'))[:],
            'select 1'
        )

    def test_getitem_slice_type(self):
        class MySelect(Select):
            pass
        q = MySelect(Sql('1'))
        self.assertTrue(isinstance(q[0:1], MySelect))

    def test_getitem_index(self):
        connection.connect(':memory:')
        connection.get_connection().rows = rows = [('row2',)]
        q = Select(sources=Sql('some_table'))
        self.assertEqual(q[1], rows[0])
        self.assertEqual(
            connection.get_connection().statements,
            [('select * from some_table limit 1, 1', ())]
        )

    def test_getitem_index_indexerror(self):
        connection.connect(':memory:')
        connection.get_connection().rows = rows = []
        q = Select(sources=Sql('some_table'))
        self.assertRaises(IndexError, q.__getitem__, 1)
        self.assertEqual(
            connection.get_connection().statements,
            [('select * from some_table limit 1, 1', ())]
        )

    def test_order_by(self):
        self.assertSqlEqual(
            Select(1).order_by(Sql('some_column'), Desc(Sql('other_column'))),
            'select ? order by some_column, other_column desc',
            (1,)
        )

    def test_order_by_type(self):
        class MySelect(Select):
            pass
        q = MySelect(Sql('1'))
        self.assertTrue(isinstance(q.order_by(Sql('some_column')), MySelect))

    def test_find(self):
        q = Select(0).find(Sql('some_column') == 1, Expr(2) + 3)
        self.assertSqlEqual(
            q,
            'select ? where (some_column = ?) and (? + ?)',
            (0, 1, 2, 3)
        )
        self.assertSqlEqual(
            q.find(Sql('other_column')),
            'select ? where ((some_column = ?) and (? + ?)) and other_column',
            (0, 1, 2, 3)
        )

    def test_find_type(self):
        class MySelect(Select):
            pass
        q = MySelect(Sql('1'))
        self.assertTrue(isinstance(q.find(Sql('1')), MySelect))

    def test_delete(self):
        q = Select(
            Sql('1'),
            Sql('some_table'),
            Sql('some_condition'),
            Desc(Sql('some_column')),
            Limit(2)
        ).delete()
        self.assertTrue(isinstance(q, Delete))
        self.assertSqlEqual(
            q,
            'delete from some_table '
            'where some_condition order by some_column desc limit 2'
        )


class TestDelete(SqlTestCase):
    def test_delete(self):
        q = Delete(Sql('some_table'))
        self.assertSqlEqual(q, 'delete from some_table')

    def test_where(self):
        q = Delete(Sql('some_table'), Expr(1) == 2)
        self.assertSqlEqual(q, 'delete from some_table where ? = ?', (1, 2))

    def test_order(self):
        q = Delete(Sql('some_table'), order=Expr(1))
        self.assertSqlEqual(q, 'delete from some_table order by ?', (1,))

    def test_limit(self):
        q = Delete(Sql('some_table'), limit=Limit(1))
        self.assertSqlEqual(q, 'delete from some_table limit 1')

    def test_all_clauses(self):
        q = Delete(Sql('some_table'), Expr(1) == 2, Expr(3), Limit(4))
        self.assertSqlEqual(
            q,
            'delete from some_table where ? = ? order by ? limit 4',
            (1, 2, 3)
        )

    def test_multiple_sources_raises_typeerror(self):
        self.assertRaises(
            TypeError,
            Delete,
            ExprList([Sql('some_table'), Sql('other_table')])
        )

    def test_order_by(self):
        self.assertSqlEqual(
            Delete(Expr(1)).order_by(
                Sql('some_column'),
                Desc(Sql('other_column'))
            ),
            'delete from ? order by some_column, other_column desc',
            (1,)
        )

    def test_order_by_type(self):
        class MyDelete(Delete):
            pass
        q = MyDelete(Sql('1'))
        self.assertTrue(isinstance(q.order_by(Sql('some_column')), MyDelete))


class TestInsert(SqlTestCase):
    def test_insert(self):
        q = Insert(
            Sql('some_table'),
            ExprList([Sql('some_column'), Sql('other_column')]),
            ExprList([2, Sql('current_timestamp')])
        )
        self.assertSqlEqual(
            q,
            'insert into some_table (some_column, other_column) '
            'values (?, current_timestamp)',
            (2,)
        )

    def test_insert_default_values(self):
        q = Insert(Sql('some_table'))
        self.assertSqlEqual(q, 'insert into some_table default values')
        q = Insert(Sql('some_table'), ExprList([Sql('some_column')]))
        self.assertSqlEqual(q, 'insert into some_table default values')

    def test_insert_values_without_columns_raises_typeerror(self):
        self.assertRaises(
            TypeError,
            Insert,
            Sql('some_table'),
            values=ExprList([1, 2, 3])
        )

    def test_insert_from_select(self):
        q = Insert(Sql('some_table'), values=Select(1))
        self.assertSqlEqual(q, 'insert into some_table select ?', (1,))
        q = Insert(
            Sql('some_table'),
            ExprList([Sql('some_column')]),
            Select(1)
        )
        self.assertSqlEqual(
            q,
            'insert into some_table (some_column) select ?',
            (1,)
        )

    def test_on_conflict(self):
        q = Insert(Sql('some_table'), on_conflict='replace')
        self.assertSqlEqual(
            q,
            'insert or replace into some_table default values'
        )


class TestUpdate(SqlTestCase):
    def test_update(self):
        q = Update(
            Sql('some_table'),
            ExprList([Sql('some_column'), Sql('other_column')]),
            ExprList([2, Sql('current_timestamp')]),
            Expr(1)
        )
        self.assertSqlEqual(
            q,
            'update some_table set '
            'some_column = ?, other_column = current_timestamp '
            'where ?',
            (2, 1)
        )

    def test_on_conflict(self):
        q = Update(
            Sql('some_table'),
            ExprList([Sql('some_column')]),
            ExprList([Sql('current_timestamp')]),
            on_conflict='replace'
        )
        self.assertSqlEqual(
            q,
            'update or replace some_table set some_column = current_timestamp'
        )


if __name__ == "__main__":
    main(__name__)
