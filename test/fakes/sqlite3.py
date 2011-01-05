def reset():
    del Connection.instances[:]


class Cursor(object):
    def __init__(self, connection):
        self.connection = connection
        self.rows = []

    def __iter__(self):
        return iter(self.rows)

    def execute(self, sql, args=()):
        self.connection.statements.append((sql, args))
        self.rows = self.connection.rows

    def executemany(self, sql, args):
        self.connection.many_statements.append((sql, args))
        self.rows = self.connection.rows

    def fetchone(self):
        if self.rows:
            return self.rows[0]

    @property
    def lastrowid(self):
        assert self.connection.statements[-1][0].startswith('insert')
        return self.connection.lastrowid


class Connection(object):
    instances = []

    def __init__(self, path):
        Connection.instances.append(self)
        self.path = path
        self.rows = []
        self.statements = []
        self.many_statements = []
        self.lastrowid = None

    def cursor(self):
        return Cursor(self)


def connect(path):
    return Connection(path)
