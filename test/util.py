import unittest


class SqlTestCase(unittest.TestCase):
    def assertSqlEqual(self, query, sql, args=()):
        self.assertEqual(query.sql(), sql)
        self.assertEqual(query.args(), args)


def main(module_name):
    import sys
    tests = unittest.defaultTestLoader.loadTestsFromModule(
        sys.modules[module_name])
    test_suite = unittest.TestSuite(tests)
    unittest.TextTestRunner(verbosity=2).run(test_suite)
