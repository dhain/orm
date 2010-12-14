import re

from .query import Expr, ExprList, Sql, Select


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

    def __init__(self, name=None):
        self.name = name
        self.attr = None
        self.model = None

    def __copy__(self):
        column = Column(self.name)
        column.attr = self.attr
        column.model = self.model
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


class Model(object):
    orm_columns = ()
    orm_alias = None

    class __metaclass__(type):
        def __init__(cls, name, bases, ns):
            if bases == (object,):
                return
            cls.orm_columns = columns = ExprList()
            for base in bases:
                for base_column in base.orm_columns:
                    column = base_column.__copy__()
                    column.model = cls
                    assert column.attr is not None
                    ns[column.attr] = column
                    setattr(cls, column.attr, column)
            for attr, value in ns.iteritems():
                if isinstance(value, Column):
                    columns.append(value)
                    if not value.name:
                        value.name = attr
                    if not value.attr:
                        value.attr = attr
                    if not value.model:
                        value.model = cls
            REGISTERED_MODELS[name] = cls

    def __new__(cls, *args, **kwargs):
        self = super(Model, cls).__new__(cls)
        self.orm_dirty = {}
        return self

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
                res[indexes[column.model]].__dict__[column.attr] = value
            yield res[0] if len(res) == 1 else tuple(res)
