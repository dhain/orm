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


class Expr(object):
    def __init__(self, value):
        self.value = value

    for class_name, op, method_name in prefix_unary_ops + postfix_unary_ops:
        eval(compile(
            ('''
                def %s(self):
                    return %s(self)
            ''' % (method_name, class_name)).strip(),
            __file__,
            'exec'
        ))
    del class_name, op, method_name

    for class_name, op, method_name in binary_ops:
        eval(compile(
            ('''
                def %s(self, other):
                    return %s(self, other)
            ''' % (method_name, class_name)).strip(),
            __file__,
            'exec'
        ))
    del class_name, op, method_name

    def sql(self):
        try:
            sql = self.value.sql
        except AttributeError:
            return '?'
        return sql()

    def args(self):
        try:
            args = self.value.args
        except AttributeError:
            return (self.value,)
        return args()


class Parenthesizing(object):
    pass


class PrefixUnaryOp(Expr, Parenthesizing):
    def sql(self):
        sql = super(PrefixUnaryOp, self).sql()
        if isinstance(self.value, Parenthesizing):
            return '%s (%s)' % (self._op, sql)
        return '%s %s' % (self._op, sql)


class PostfixUnaryOp(Expr, Parenthesizing):
    def sql(self):
        sql = super(PostfixUnaryOp, self).sql()
        if isinstance(self.value, Parenthesizing):
            return '(%s) %s' % (sql, self._op)
        return '%s %s' % (sql, self._op)


for class_name, op, method_name in prefix_unary_ops:
    locals()[class_name] = type(class_name, (PrefixUnaryOp,), dict(_op=op))
del class_name, op, method_name, prefix_unary_ops


for class_name, op, method_name in postfix_unary_ops:
    locals()[class_name] = type(class_name, (PostfixUnaryOp,), dict(_op=op))
del class_name, op, method_name, postfix_unary_ops


class BinaryOp(Expr, Parenthesizing):
    def __init__(self, lvalue, rvalue):
        self.lvalue = lvalue if isinstance(lvalue, Expr) else Expr(lvalue)
        self.rvalue = rvalue if isinstance(rvalue, Expr) else Expr(rvalue)

    def sql(self):
        lsql = self.lvalue.sql()
        if isinstance(self.lvalue, Parenthesizing):
            lsql = '(%s)' % (lsql,)
        rsql = self.rvalue.sql()
        if isinstance(self.rvalue, Parenthesizing):
            rsql = '(%s)' % (rsql,)
        return '%s %s %s' % (lsql, self._op, rsql)

    def args(self):
        return self.lvalue.args() + self.rvalue.args()


for class_name, op, method_name in binary_ops:
    locals()[class_name] = type(class_name, (BinaryOp,), dict(_op=op))
del class_name, op, method_name, binary_ops


class Sql(Expr):
    def sql(self):
        return self.value

    def args(self):
        return ()


class Select(Expr, Parenthesizing):
    def sql(self):
        return 'select ' + super(Select, self).sql()
