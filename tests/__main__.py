import unittest
import sys
from os.path import abspath, dirname

sys.path.append(abspath(dirname(__file__) + '/..'))

unittest.main(module='camera_tests')
