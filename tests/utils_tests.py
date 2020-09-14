# -*- coding: utf-8 -*-

import unittest
import os.path
import json
import sys

from datetime import datetime as dt, tzinfo
import pytz

import unifi_video.utils

class UtilitiesTests(unittest.TestCase):

    def test_utc_offset_parsing(self):

        test_pairs = (
            ('GMT+5',      5 * 3600),
            ('GMT-5',     -5 * 3600),
            ('GMT-05',    -5 * 3600),
            ('GMT+05',     5 * 3600),
            ('GMT+05:04',  5 * 3600 + 4 * 60),
            ('GMT+05:4',   5 * 3600 + 4 * 60),
            ('GMT+5:4',    5 * 3600 + 4 * 60),
            ('GMT+05:42',  5 * 3600 + 42 * 60),
            ('GMT+5:42',   5 * 3600 + 42 * 60),
            ('GMT+5:42',   5 * 3600 + 42 * 60),
            ('GMT-05:04', -5 * 3600 + -4 * 60),
            ('GMT-05:4',  -5 * 3600 + -4 * 60),
            ('GMT-5:4',   -5 * 3600 + -4 * 60),
            ('GMT-05:42', -5 * 3600 + -42 * 60),
            ('GMT-5:42',  -5 * 3600 + -42 * 60),
            ('GMT-5:42',  -5 * 3600 + -42 * 60),
            ('GMT-00:04', -4 * 60),
            ('GMT-0:04',  -4 * 60),
            ('GMT+00:04',  4 * 60),
            ('GMT+0:04',   4 * 60),
        )

        for test_pair in test_pairs:
            self.assertEqual(
                test_pair[1],
                unifi_video.utils.parse_gmt_offset(test_pair[0]))

if __name__ == '__main__':
    unittest.main()
