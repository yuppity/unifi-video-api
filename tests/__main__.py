import unittest
import sys
from os.path import abspath, dirname

sys.path.append(abspath(dirname(__file__) + '/..'))

errors_and_failures = 0

for test_program in [
            unittest.main(module='camera_tests', exit=False),
            unittest.main(module='api', exit=False),
            unittest.main(module='utils_tests', exit=False),
        ]:
    errors_and_failures += len(test_program.result.errors)
    errors_and_failures += len(test_program.result.failures)

if errors_and_failures:
    sys.exit(1)
