binary_ops = [
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
    ('Like', 'like', 'like'),
    ('Glob', 'glob', 'glob'),
    ('Match', 'match', 'match'),
    ('Regexp', 'regexp', 'regexp'),
]

unary_ops = [
    ('Not', 'not', '__invert__'),
    ('Pos', '+', '__pos__'),
    ('Neg', '-', '__neg__'),
]


class Expr(object):
    def __init__(self, value):
        self.value = value

    for class_name, op, method_name in unary_ops:
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


class UnaryOp(Expr):
    def sql(self):
        return '%s %s' % (self._op, super(UnaryOp, self).sql())


for class_name, op, method_name in unary_ops:
    locals()[class_name] = type(class_name, (UnaryOp,), dict(_op=op))
del class_name, op, unary_ops


class BinaryOp(Expr):
    def __init__(self, lvalue, rvalue):
        self.lvalue = lvalue if isinstance(lvalue, Expr) else Expr(lvalue)
        self.rvalue = rvalue if isinstance(rvalue, Expr) else Expr(rvalue)

    def sql(self):
        return '%s %s %s' % (self.lvalue.sql(), self._op, self.rvalue.sql())

    def args(self):
        return self.lvalue.args() + self.rvalue.args()


for class_name, op, method_name in binary_ops:
    locals()[class_name] = type(class_name, (BinaryOp,), dict(_op=op))
del class_name, op, binary_ops


class Sql(Expr):
    def sql(self):
        return self.value

    def args(self):
        return ()


class Select(Expr):
    def sql(self):
        return 'select ' + super(Select, self).sql()
