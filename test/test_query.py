import unittest

from .util import SqlTestCase

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


class TestSelect(SqlTestCase):
    def test_basic_value(self):
        self.assertSqlEqual(Select(1), 'select ?', (1,))

    def test_sql_value(self):
        sql = 'some raw sql string'
        self.assertSqlEqual(Select(Sql(sql)), 'select %s' % (sql,))


if __name__ == "__main__":
    import sys
    tests = unittest.defaultTestLoader.loadTestsFromModule(
        sys.modules[__name__])
    test_suite = unittest.TestSuite(tests)
    unittest.TextTestRunner(verbosity=2).run(test_suite)
