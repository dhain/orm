import re

from .query import Expr, ExprList, Sql, Select


class Column(Expr):
    def __init__(self, name=None):
        self.name = name
        self.attr = None
        self.model = None

    def sql(self):
        if not self.name:
            raise TypeError('column must have a name')
        if self.model:
            return '%s."%s"' % (self.model.sql(), self.name)
        return '"%s"' % (self.name,)

    def args(self):
        return ()


class Model(object):
    class __metaclass__(type):
        def __init__(cls, name, bases, ns):
            if bases == (object,):
                return
            columns = []
            for attr, value in ns.iteritems():
                if isinstance(value, Column):
                    columns.append(value)
                    if not value.name:
                        value.name = attr
                    if not value.attr:
                        value.attr = attr
                    if not value.model:
                        value.model = cls
            if 'orm_columns' not in ns:
                cls.orm_columns = tuple(columns)

    @classmethod
    def find(cls, *where):
        q = ModelSelect(ExprList(cls.orm_columns), cls)
        if where:
            q = q.find(*where)
        return q

    @classmethod
    def sql(cls):
        return '"%s"' % (cls.orm_table,)

    @classmethod
    def args(cls):
        return ()


class ModelSelect(Select):
    def __iter__(self):
        for row in super(ModelSelect, self).__iter__():
            obj = self.sources.__new__(self.sources)
            for column, value in zip(self.what, row):
                setattr(obj, column.attr, value)
            yield obj
