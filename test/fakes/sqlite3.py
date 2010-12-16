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


class Connection(object):
    instances = []

    def __init__(self, path):
        Connection.instances.append(self)
        self.path = path
        self.rows = []
        self.statements = []
        self.many_statements = []

    def cursor(self):
        return Cursor(self)


def connect(path):
    return Connection(path)
