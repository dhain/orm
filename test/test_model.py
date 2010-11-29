import unittest


class TestModel(unittest.TestCase):
    pass


if __name__ == "__main__":
    import sys
    tests = unittest.defaultTestLoader.loadTestsFromModule(
        sys.modules[__name__])
    test_suite = unittest.TestSuite(tests)
    unittest.TextTestRunner(verbosity=2).run(test_suite)
