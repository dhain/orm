import unittest


class SqlTestCase(unittest.TestCase):
    def assertSqlEqual(self, query, sql, args=()):
        self.assertEqual(query.sql(), sql)
        self.assertEqual(query.args(), args)

    def assertItemsIdentical(self, seq1, seq2):
        seq1 = iter(seq1)
        seq2 = iter(seq2)
        for i, (obj1, obj2) in enumerate(zip(seq1, seq2)):
            self.assertTrue(
                obj2 is obj1,
                'items at %d differ: %r is not %r' % (i, obj2, obj1)
            )
        self.assertEqual(list(seq1), [], 'seq1 is bigger than seq2')
        self.assertEqual(list(seq2), [], 'seq2 is bigger than seq1')

    def assertColumnEqual(self, column, value):
        self.assertTrue(
            (column == value) is True,
            '%r != %r' % (column, value)
        )


def main(module_name):
    import sys
    tests = unittest.defaultTestLoader.loadTestsFromModule(
        sys.modules[module_name])
    test_suite = unittest.TestSuite(tests)
    unittest.TextTestRunner(verbosity=2).run(test_suite)
