from . import connection


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
        exec ('''
            def %s(self):
                return %s(self)
        ''' % (method_name, class_name)).strip()
    del class_name, op, method_name

    for class_name, op, method_name in binary_ops:
        exec ('''
            def %s(self, other):
                return %s(self, other)
        ''' % (method_name, class_name)).strip()
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

    def execute(self):
        cur = connection.get_connection().cursor()
        cur.execute(self.sql(), self.args())
        return cur


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


class ExprList(list, Expr, Parenthesizing):
    _no_sequence = object()

    def __init__(self, sequence=_no_sequence):
        if sequence is ExprList._no_sequence:
            return super(ExprList, self).__init__()
        return super(ExprList, self).__init__((
            item if isinstance(item, Expr) else Expr(item)
            for item in sequence
        ))

    def append(self, object):
        super(ExprList, self).append(
            object if isinstance(object, Expr) else Expr(object))

    def extend(self, iterable):
        super(ExprList, self).extend((
            object if isinstance(object, Expr) else Expr(object)
            for object in iterable
        ))

    def insert(self, index, object):
        super(ExprList, self).insert(index,
            object if isinstance(object, Expr) else Expr(object))

    def __getitem__(self, y):
        if isinstance(y, (int, long)):
            return super(ExprList, self).__getitem__(y)
        return ExprList(super(ExprList, self).__getitem__(y))

    def __getslice__(self, i, j):
        return ExprList(super(ExprList, self).__getslice__(i, j))

    def __setitem__(self, i, y):
        if isinstance(i, (int, long)):
            super(ExprList, self).__setitem__(i,
                y if isinstance(y, Expr) else Expr(y))
        else:
            super(ExprList, self).__setitem__(i, ExprList(y))

    def __setslice__(self, i, j, y):
        super(ExprList, self).__setslice__(i, j, ExprList(y))

    def __add__(self, other):
        ret = self[:]
        ret.extend(other)
        return ret

    def __iadd__(self, other):
        self.extend(other)
        return self

    def __mul__(self, n):
        return ExprList(super(ExprList, self).__mul__(n))

    __rmul__ = __mul__

    def sql(self):
        items = ((item.sql(), isinstance(item, Parenthesizing))
                 for item in self)
        return ', '.join(
            '(%s)' % (sql,) if paren else sql
            for sql, paren in items
        )

    def args(self):
        args = []
        for item in self:
            args.extend(item.args())
        return tuple(args)


class Asc(Expr):
    def sql(self):
        return super(Asc, self).sql() + ' asc'


class Desc(Expr):
    def sql(self):
        return super(Desc, self).sql() + ' desc'


class Limit(Sql):
    def __init__(self, limit_slice):
        if isinstance(limit_slice, (int, long)):
            limit_slice = slice(limit_slice)
        if limit_slice.step is not None:
            raise TypeError('step is not supported')
        if (
            (limit_slice.stop is not None and limit_slice.stop < 0) or
            (limit_slice.start is not None and limit_slice.start < 0)
        ):
            raise NotImplementedError('negative slice values not supported')
        if (
            (limit_slice.stop is not None and
             not isinstance(limit_slice.stop, (int, long))) or
            (limit_slice.start is not None and
             not isinstance(limit_slice.start, (int, long)))
        ):
            raise TypeError('slice values must be numbers')
        if (
            limit_slice.start is not None and
            limit_slice.stop is not None and
            limit_slice.stop < limit_slice.start
        ):
            raise ValueError('stop must be greater than start')
        self.offset = limit_slice.start
        self.limit = (None if limit_slice.stop is None else (
            limit_slice.stop if limit_slice.start is None
            else limit_slice.stop - limit_slice.start))

    def sql(self):
        if self.offset is None and self.limit is None:
            return ''
        if self.offset is None:
            return 'limit %d' % (self.limit,)
        if self.limit is None:
            return 'limit %d, -1' % (self.offset,)
        return 'limit %d, %d' % (self.offset, self.limit)


class Select(Expr, Parenthesizing):
    def __init__(self, what=None, sources=None,
                 where=None, order=None, limit=None):
        if what is None:
            if sources is None:
                raise TypeError('must specify sources if not specifying what')
            self.what = Sql('*')
        else:
            self.what = what if isinstance(what, Expr) else Expr(what)
        self.sources = sources
        self.where = where
        self.order = order
        self.limit = limit

    def order_by(self, *args):
        if args:
            order = ExprList(args)
        else:
            order = None
        return type(self)(
            self.what, self.sources, self.where, order, self.limit)

    def find(self, where, *ands):
        if not isinstance(where, Expr):
            where = Expr(where)
        if ands:
            where = reduce(And, ands, where)
        if self.where:
            where = self.where & where
        return type(self)(
            self.what, self.sources, where, self.order, self.limit)

    def delete(self):
        return Delete(self.sources, self.where, self.order, self.limit)

    def exists(self):
        q = Select(Sql('1'), self.sources, self.where, limit=Limit(1))
        return q.execute().fetchone() is not None

    def __len__(self):
        q = Select(Sql('count(*)'), self.sources, self.where)
        n = q.execute().fetchone()[0]
        if self.limit is not None:
            if self.limit.offset:
                n -= self.limit.offset
            if self.limit.limit is not None and n > self.limit.limit:
                return self.limit.limit
            if n < 0:
                return 0
        return n

    def __iter__(self):
        return iter(self.execute())

    def __getitem__(self, y):
        q = type(self)(self.what, self.sources, self.where, self.order)
        if isinstance(y, (int, long)):
            q.limit = Limit(slice(y, y + 1))
            try:
                return iter(q).next()
            except StopIteration:
                raise IndexError(y)
        else:
            q.limit = Limit(y)
            return q

    def sql(self):
        sql = 'select ' + self.what.sql()
        if self.sources is not None:
            sql += ' from ' + self.sources.sql()
        if self.where is not None:
            sql += ' where ' + self.where.sql()
        if self.order is not None:
            sql += ' order by ' + self.order.sql()
        if self.limit is not None:
            limit = self.limit.sql()
            if limit:
                sql += ' ' + limit
        return sql

    def args(self):
        args = list(self.what.args())
        if self.sources is not None:
            args.extend(self.sources.args())
        if self.where is not None:
            args.extend(self.where.args())
        if self.order is not None:
            args.extend(self.order.args())
        if self.limit is not None:
            args.extend(self.limit.args())
        return tuple(args)


class Delete(Expr):
    def __init__(self, sources, where=None, order=None, limit=None):
        if isinstance(sources, ExprList) and len(sources) > 1:
            raise TypeError("can't delete from more than one table")
        self.sources = sources
        self.where = where
        self.order = order
        self.limit = limit

    def order_by(self, *args):
        if args:
            order = ExprList(args)
        else:
            order = None
        return type(self)(self.sources, self.where, order, self.limit)

    def sql(self):
        sql = 'delete from ' + self.sources.sql()
        if self.where is not None:
            sql += ' where ' + self.where.sql()
        if self.order is not None:
            sql += ' order by ' + self.order.sql()
        if self.limit is not None:
            limit = self.limit.sql()
            if limit:
                sql += ' ' + limit
        return sql

    def args(self):
        args = list(self.sources.args())
        if self.where is not None:
            args.extend(self.where.args())
        if self.order is not None:
            args.extend(self.order.args())
        if self.limit is not None:
            args.extend(self.limit.args())
        return tuple(args)


class Insert(Expr):
    def __init__(self, model, columns=None, values=None, on_conflict=None):
        self.model = model
        self.columns = columns
        self.values = values
        self.on_conflict = on_conflict

    def sql(self):
        sql = 'insert'
        if self.on_conflict is not None:
            sql += ' or ' + self.on_conflict
        sql += ' into ' + self.model.sql()
        if self.values is None:
            sql += ' default values'
            return sql
        if self.columns is not None:
            sql += ' (' + self.columns.sql() + ')'
        if isinstance(self.values, Select):
            sql += ' ' + self.values.sql()
        else:
            sql += ' values (' + self.values.sql() + ')'
        return sql

    def args(self):
        args = list(self.model.args())
        if self.columns is not None:
            args.extend(self.columns.args())
        if self.values is not None:
            args.extend(self.values.args())
        return tuple(args)


class Update(Expr):
    def __init__(self, model, columns, values, where=None, on_conflict=None):
        self.model = model
        self.columns = columns
        self.values = values
        self.where = where
        self.on_conflict = on_conflict

    def sql(self):
        sql = 'update'
        if self.on_conflict is not None:
            sql += ' or ' + self.on_conflict
        sql += ' ' + self.model.sql()
        sql += ' set ' + ExprList(
            Sql('%s=%s' % (column.sql(), value.sql()))
            for column, value in zip(self.columns, self.values)
        ).sql()
        if self.where is not None:
            sql += ' where ' + self.where.sql()
        return sql

    def args(self):
        args = list(self.model.args())
        args.extend(self.columns.args())
        args.extend(self.values.args())
        if self.where is not None:
            args.extend(self.where.args())
        return tuple(args)
