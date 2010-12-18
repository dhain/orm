import re

from .query import *


all_ignore = set(locals())
all_ignore.add('all_ignore')


REGISTERED_MODELS = {}


def dereference_column(name):
    model_name, column_attr = name.split('.', 1)
    try:
        return getattr(REGISTERED_MODELS[model_name], column_attr)
    except KeyError:
        raise RuntimeError('unknown model %r' % (model_name,))
    except AttributeError:
        raise RuntimeError('unknown column %r' % (name,))


class Column(Expr):
    no_value = object()

    def __init__(self, name=None, primary=False):
        self.name = name
        self.attr = None
        self.model = None
        self.primary = primary

    def __copy__(self):
        column = Column(self.name)
        column.attr = self.attr
        column.model = self.model
        column.primary = self.primary
        return column

    def __set__(self, obj, value):
        obj.orm_dirty[self] = obj.__dict__.get(self.attr, Column.no_value)
        obj.__dict__[self.attr] = value

    def sql(self):
        if not self.name:
            raise TypeError('column must have a name')
        if self.model:
            return '%s."%s"' % (self.model.alias_sql(), self.name)
        return '"%s"' % (self.name,)

    def args(self):
        return ()


class ToOne(object):
    def __init__(self, my_column, other_column):
        self.my_column = my_column
        self.other_column = other_column

    def _dereference(self):
        if isinstance(self.other_column, basestring):
            self.other_column = dereference_column(self.other_column)

    def __get__(self, obj, cls):
        if obj is None:
            return self
        self._dereference()
        value = getattr(obj, self.my_column.attr)
        q = self.other_column.model.find(self.other_column == value)
        try:
            return q[0]
        except IndexError:
            return None

    def __set__(self, obj, other):
        self._dereference()
        value = getattr(other, self.other_column.attr)
        setattr(obj, self.my_column.attr, value)


class ToMany(object):
    def __init__(self, my_column, other_column):
        self.my_column = my_column
        self.other_column = other_column

    def _dereference(self):
        if isinstance(self.other_column, basestring):
            self.other_column = dereference_column(self.other_column)

    def __get__(self, obj, cls):
        if obj is None:
            return self
        self._dereference()
        value = getattr(obj, self.my_column.attr)
        return self.other_column.model.find(self.other_column == value)

    def __set__(self, obj, value):
        raise AttributeError("can't set attribute")


class ManyToMany(object):
    def __init__(self, my_column, my_join, other_join, other_column):
        self.my_column = my_column
        self.my_join = my_join
        self.other_join = other_join
        self.other_column = other_column

    def _dereference(self):
        if isinstance(self.my_join, basestring):
            self.my_join = dereference_column(self.my_join)
        if isinstance(self.other_join, basestring):
            self.other_join = dereference_column(self.other_join)
        if isinstance(self.other_column, basestring):
            self.other_column = dereference_column(self.other_column)

    def __get__(self, obj, cls):
        if obj is None:
            return self
        self._dereference()
        value = getattr(obj, self.my_column.attr)
        q = self.other_column.model.find(
            self.my_join == value,
            self.other_join == self.other_column
        )
        q.sources = ExprList([self.other_column.model, self.other_join.model])
        return q

    def __set__(self, obj, value):
        raise AttributeError("can't set attribute")


class Model(object):
    orm_new = True
    orm_columns = ()
    orm_primaries = ()
    orm_alias = None

    class __metaclass__(type):
        def __init__(cls, name, bases, ns):
            if bases == (object,):
                return
            cls.orm_columns = columns = ExprList()
            cls.orm_primaries = primaries = ExprList()
            for base in bases:
                for base_column in base.orm_columns:
                    column = base_column.__copy__()
                    column.model = cls
                    assert column.attr is not None
                    setattr(cls, column.attr, column)
                    columns.append(column)
                    if column.primary:
                        primaries.append(column)
            for attr, value in ns.iteritems():
                if isinstance(value, Column):
                    columns.append(value)
                    if not value.name:
                        value.name = attr
                    if not value.attr:
                        value.attr = attr
                    if not value.model:
                        value.model = cls
                    if value.primary:
                        primaries.append(value)
            REGISTERED_MODELS[name] = cls

    def __new__(cls, *args, **kwargs):
        self = super(Model, cls).__new__(cls)
        self.orm_dirty = {}
        return self

    def save(self):
        if not (self.orm_new or self.orm_dirty):
            return
        if self.orm_new:
            q = Insert(
                self,
                ExprList(
                    Sql('"%s"' % (column.name,))
                    for column in self.orm_dirty
                ) or None,
                ExprList(
                    getattr(self, column.attr)
                    for column in self.orm_dirty
                ) or None
            )
        else:
            where = reduce(And, (
                column == self.orm_dirty.get(
                    column, getattr(self, column.attr))
                for column in self.orm_primaries or self.orm_columns
            ))
            q = Update(
                self,
                ExprList(
                    Sql('"%s"' % (column.name,))
                    for column in self.orm_dirty
                ),
                ExprList(
                    getattr(self, column.attr)
                    for column in self.orm_dirty
                ),
                where
            )
        q.execute()
        self.orm_new = False
        self.orm_dirty.clear()

    @classmethod
    def find(cls, *where):
        q = ModelSelect(ExprList(cls.orm_columns), cls)
        if where:
            q = q.find(*where)
        return q

    @classmethod
    def as_alias(cls, alias):
        return type(
            '%s_as_%s' % (cls.__name__, alias),
            (cls,),
            dict(orm_alias=alias)
        )

    @classmethod
    def alias_sql(cls):
        if cls.orm_alias:
            return '"%s"' % (cls.orm_alias,)
        return cls.sql()

    @classmethod
    def sql(cls):
        if cls.orm_alias:
            return '"%s" "%s"' % (cls.orm_table, cls.orm_alias)
        return '"%s"' % (cls.orm_table,)

    @classmethod
    def args(cls):
        return ()


class ModelSelect(Select):
    def __iter__(self):
        for row in super(ModelSelect, self).__iter__():
            res = []
            indexes = {}
            for column, value in zip(self.what, row):
                if column.model not in indexes:
                    indexes[column.model] = len(res)
                    res.append(column.model.__new__(column.model))
                    res[-1].orm_new = False
                res[indexes[column.model]].__dict__[column.attr] = value
            yield res[0] if len(res) == 1 else tuple(res)


__all__ = list(set(locals()) - all_ignore)
