import re

from .query import Expr, Sql, Select


class Column(Expr):
    def __init__(self, name):
        self.name = name

    def __get__(self, obj, cls):
        return BoundColumn(self, cls)

    def sql(self):
        return '"%s"' % (self.name,)

    def args(self):
        return ()


class BoundColumn(Column):
    def __init__(self, column, model):
        self.column = column
        self.model = model

    def sql(self):
        return '"%s".%s' % (self.model.orm_table, self.column.sql())


class Model(object):
    @classmethod
    def find(cls, *where):
        q = Select(sources=Sql('"%s"' % (cls.orm_table,)))
        if where:
            q = q.find(*where)
        return q
