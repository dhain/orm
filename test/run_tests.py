import imp
import re
import os
import sys
import unittest


def _load_tests_from_file(path):
    parent, filename = os.path.split(path)
    dotted_parent = '.'.join(parent.split('/'))
    if dotted_parent not in sys.modules:
        imp.load_source(dotted_parent, os.path.join(parent, '__init__.py'))
    dotted_path = '%s.%s' % (dotted_parent, os.path.splitext(filename)[0])
    module = imp.load_source(dotted_path, path)
    return unittest.defaultTestLoader.loadTestsFromModule(module)


def _load_tests_from_dir(path, exclude=()):
    _test_re = re.compile('test_.+?\.py$', re.IGNORECASE)
    return [
        _load_tests_from_file(os.path.join(path, filename))
        for filename in os.listdir(path)
        if _test_re.match(filename) and filename not in exclude
    ]


if __name__ == "__main__":
    sys.path[0:0] = [os.getcwd()]
    path, exclude = os.path.split(__file__)
    tests = []
    if sys.argv[1:] in ([], ['all']):
        tests.extend(_load_tests_from_dir(path, [exclude]))
    if sys.argv[1:] == ['all']:
        for test_dir in os.listdir(path):
            test_dir_path = os.path.join(path, test_dir)
            if os.path.isdir(test_dir_path):
                tests.extend(_load_tests_from_dir(test_dir_path))
    else:
        for test_path in sys.argv[1:]:
            test_path_path = os.path.join(path, test_path)
            if os.path.isdir(test_path_path):
                tests.extend(_load_tests_from_dir(test_path_path))
            elif os.path.isfile(test_path_path):
                tests.extend(_load_tests_from_file(test_path_path))
    test_suite = unittest.TestSuite(tests)
    unittest.TextTestRunner(verbosity=2).run(test_suite)
