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

    def test_dt_resolving(self):

        meaningless_offset = 829869263

        test_pairs = (
            (('1970-01-01T00:00'      ,          0 * 3600) , 0)          ,
            (('1970-01-01T01:00'      ,          0 * 3600) , 3.6e3)      ,
            (('1970-01-01T01:00'      ,          1 * 3600) , 0)          ,
            (('1970-01-01T01:00'      ,          2 * 3600) , -3.6e3)     ,
            (((1970, 1, 1, 1, 0)      , 'Europe/Helsinki') , -3.6e3)     ,
            (('2020-03-03T23:11:22'   ,          0 * 3600) , 1583277060) ,
            (('2020-03-03T23:11:21'   ,          0 * 3600) , 1583277060) ,
            (('2020-03-03T23:11'      ,          0 * 3600) , 1583277060) ,
            (('2020-03-03 23:11:22'   ,          0 * 3600) , 1583277060) ,
            (('2020-03-03 23:11:21'   ,          0 * 3600) , 1583277060) ,
            (('2020-03-03 23:11'      ,          0 * 3600) , 1583277060) ,
            (('2020-03-03T23:11'      ,          0 * 3600) , 1583277060) ,
            (('20200303T23:11'        ,          0 * 3600) , 1583277060) ,
            (('20200303T2311'         ,          0 * 3600) , 1583277060) ,
            (('2020030323:11'         ,          0 * 3600) , 1583277060) ,
            (('202003032311'          ,          0 * 3600) , 1583277060) ,
            (('202003032311Z'         ,          0 * 3600) , 1583277060) ,
            (('202003032311+00:00'    ,          0 * 3600) , 1583277060) ,
            (('202003032311+03:00'    ,          0 * 3600) , 1583277060) ,
            (('2020-03-03T23:10:21'   ,          0 * 3600) , 1583277000) ,
            (('2020-03-03T23:10:21Z'  ,          0 * 3600) , 1583277000) ,
            (('2020-03-03T23:10:2124' ,          0 * 3600) , 1583277000) ,
            (('2020-03-03T23:10blah'  ,          0 * 3600) , 1583277000) ,
            (('2020-03-03T2310blah'   ,          0 * 3600) , 1583277000) ,
            (('2020-03-03 2310blah'   ,          0 * 3600) , 1583277000) ,
            (('2020-03-032310blah'    ,          0 * 3600) , 1583277000) ,
            (('2020-03-03230blah'     ,          0 * 3600) , 1583276400) ,
            (('2020-aa-032310blah'    ,          0 * 3600) , ValueError) ,
            (('2020-00-032310blah'    ,          0 * 3600) , ValueError) ,
            (('a2020-00-032310blah'   ,          0 * 3600) , ValueError) ,
            (('a020-03-002310blah'    ,          0 * 3600) , ValueError) ,
            ((0                       ,          0 * 3600) , 0)          ,
            ((0                       ,          2 * 3600) , 0)          ,
            (('2019-10-02T23:11:00'   ,          0 * 3600) , 1570057860) ,
            ((dt(2019, 10, 2, 23, 11) ,          0 * 3600) , 1570057860) ,
            (((2017, 10, 2, 23, 11)   , 'Europe/Helsinki') , 1506975060) ,
        )

        for test_pair in test_pairs:
            try:
                if isinstance(test_pair[0][1], str):
                    print(test_pair[0][0])
                    self.assertEqual(
                        test_pair[1] * 1000,
                        unifi_video.utils.dt_resolvable_to_ms(
                            pytz.timezone(test_pair[0][1]).localize(
                                dt(*test_pair[0][0])),
                            meaningless_offset))
                elif isinstance(test_pair[1], (int, float)):
                    self.assertEqual(
                        test_pair[1] * 1000,
                        unifi_video.utils.dt_resolvable_to_ms(*test_pair[0]))
                elif issubclass(test_pair[1], Exception):
                    self.assertRaises(
                        test_pair[1],
                        unifi_video.utils.dt_resolvable_to_ms,
                        *test_pair[0])
            except AssertionError as e:
                raise AssertionError('{} ({})'.format(str(e), test_pair[0]))

if __name__ == '__main__':
    unittest.main()
