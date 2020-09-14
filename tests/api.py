# -*- coding: utf-8 -*-

from __future__ import print_function

import unittest
import os.path
import json
import sys

from copy import deepcopy

try:
    from mock import Mock, patch, MagicMock
except ModuleNotFoundError:
    from unittest.mock import Mock, patch, MagicMock

try:
    from urllib.parse import urljoin, urlparse, urlunparse
except ImportError:
    from urlparse import urljoin, urlparse, urlunparse

try:
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import urlopen, Request, HTTPError

from helpers import mocked_response, get_ufva_w_mocked_urlopen, \
        empty_response
from unifi_video import UnifiVideoAPI, CameraModelError, \
    UnifiVideoVersionError

import files


py3 = sys.version_info[0] == 3

responses = {}

with open(os.path.join(os.path.dirname(__file__),
        'files/camera.json'), 'rb') as f:
    responses['camera'] = f.read()

with open(os.path.join(os.path.dirname(__file__),
        'files/bootstrap.json'), 'rb') as f:
    responses['bootstrap'] = f.read()

with open(os.path.join(os.path.dirname(__file__),
        'files/recordings.json'), 'rb') as f:
    responses['recordings'] = f.read()

class APITests(unittest.TestCase):

    @patch('unifi_video.api.urlopen')
    def test_init_against_bootstrap(self, mocked_urlopen):
        """Test API init against fresh bootstrap.json

        Run through bootstrap JSONs from various UniFi Video versions.
        """

        for bootstrap in files.test_files['bootstrap.json']:
            with open(
                    os.path.join(
                        os.path.dirname(__file__),
                        'files/{}'.format(bootstrap['filename'])),
                    'rb') as f:
                bootstrap_json = f.read()

            mocked_urlopen.side_effect = mocked_response(
                arg_pile=[
                    # For  GET /recording?...
                    {'data': json.dumps(empty_response).encode('utf8')},
                    # For GET /camera
                    {'data': json.dumps(empty_response).encode('utf8')},
                    # For GET /bootstrap
                    {'data': bootstrap_json }
                ],
                set_cookies=True)

            uva = UnifiVideoAPI(api_key='xxx')

            self.assertEqual(len(uva.cameras), 0)
            self.assertEqual(len(uva.recordings), 0)
            self.assertEqual(uva.version, bootstrap['unifi_video_version'])

    @patch('unifi_video.api.urlopen')
    def test_aa_api_init(self, mocked_urlopen):
        """Test API init

        UnifiVideoAPI should:
          - throw ValueError when called without usermame-password pair
            or API key
          - throw UnifiVideoVersionError when check_ufv_version == True
            and GET bootstrap response has an unknown version string
          - throw UnifiVideoVersionError when check_ufv_version == True
            and GET bootstrap response has an out of range version
        """

        self.assertRaises(ValueError, UnifiVideoAPI)

        # Invalid version
        res_w_unk_ufv_ver = json.loads(responses['bootstrap'])
        res_w_unk_ufv_ver['data'][0]['systemInfo']['version'] = 'qwerty'

        mocked_urlopen.side_effect = mocked_response(json.dumps(
            res_w_unk_ufv_ver).encode('utf8'), set_cookies=True)

        self.assertRaises(UnifiVideoVersionError, UnifiVideoAPI,
            api_key='xxxxxx')

        # Version Lower than range
        res_w_low_ufv_ver = json.loads(responses['bootstrap'])
        res_w_low_ufv_ver['data'][0]['systemInfo']['version'] = '0.0.1'

        mocked_urlopen.side_effect = mocked_response(json.dumps(
            res_w_low_ufv_ver).encode('utf8'), set_cookies=True)

        self.assertRaises(UnifiVideoVersionError, UnifiVideoAPI,
            api_key='xxxxxx')

        # Version Higher than range
        res_w_high_ufv_ver = json.loads(responses['bootstrap'])
        res_w_high_ufv_ver['data'][0]['systemInfo']['version'] = '99999.0.0'

        mocked_urlopen.side_effect = mocked_response(json.dumps(
            res_w_high_ufv_ver).encode('utf8'), set_cookies=True)

        self.assertRaises(UnifiVideoVersionError, UnifiVideoAPI,
            api_key='xxxxxx')

        # Version in ok range
        res_w_ok_ufv_ver = json.loads(responses['bootstrap'])
        res_w_ok_ufv_ver['data'][0]['systemInfo']['version'] = '3.10.6'


        mocked_urlopen.side_effect = mocked_response(arg_pile=[
            {'data': responses['recordings']},
            {'data': responses['camera']},
            {'data': json.dumps(res_w_ok_ufv_ver).encode('utf8')},
        ])

        self.assertIsInstance(UnifiVideoAPI(api_key='xxxxx'), UnifiVideoAPI)


class CollectionTests(unittest.TestCase):

    @patch('unifi_video.api.urlopen')
    def test_collections(self, mocked_urlopen):
        '''Camera collections should be clear of any stales after refresh
        '''

        def oid(i):
            return '{:024d}'.format(i)

        bootstrap_version = '3.10.13'
        sample_camera = json.loads(responses['camera'].decode('utf8'))

        stages = [[
                {'managed': True,  'state': 'CONNECTED',    '_id': 0},
                {'managed': True,  'state': 'CONNECTED',    '_id': 1},
                {'managed': True,  'state': 'CONNECTED',    '_id': 2},
                {'managed': True,  'state': 'DISCONNECTED', '_id': 3},
                {'managed': True,  'state': 'DISCONNECTED', '_id': 4},
                {'managed': False, 'state': 'CONNECTED',    '_id': 5},
                {
                    'cameras':         {'ids': (0, 1, 2, 3, 4, 5)},
                    'managed_cameras': {'ids': (0, 1, 2, 3, 4)},
                    'active_cameras':  {'ids': (0, 1, 2)},
                }
            ], [
                {'managed': True,  'state': 'CONNECTED',    '_id': 0},
                {'managed': True,  'state': 'CONNECTED',    '_id': 1},
                {'managed': True,  'state': 'DISCONNECTED', '_id': 2},
                {'managed': True,  'state': 'DISCONNECTED', '_id': 3},
                {'managed': True,  'state': 'DISCONNECTED', '_id': 4},
                {'managed': False, 'state': 'CONNECTED',    '_id': 5},
                {
                    'cameras':         {'ids': (0, 1, 2, 3, 4, 5)},
                    'managed_cameras': {'ids': (0, 1, 2, 3, 4)},
                    'active_cameras':  {'ids': (0, 1)},
                }
            ], [
                {'managed': False, 'state': 'CONNECTED',    '_id': 5},
                {
                    'cameras':         {'ids': (5,)},
                    'managed_cameras': {'ids': ()},
                    'active_cameras':  {'ids': ()},
                }
            ], [
                {'managed': True,  'state': 'DISCONNECTED', '_id': 0},
                {'managed': True,  'state': 'DISCONNECTED', '_id': 1},
                {'managed': True,  'state': 'DISCONNECTED', '_id': 2},
                {'managed': True,  'state': 'DISCONNECTED', '_id': 3},
                {'managed': True,  'state': 'DISCONNECTED', '_id': 4},
                {'managed': False, 'state': 'CONNECTED',    '_id': 5},
                {'managed': True,  'state': 'CONNECTED',    '_id': 6},
                {
                    'cameras':         {'ids': (0, 1, 2, 3, 4, 5, 6)},
                    'managed_cameras': {'ids': (0, 1, 2, 3, 4, 6)},
                    'active_cameras':  {'ids': (6,)},
                }
            ],
        ]

        def def_camera_data(fields):
            fields['_id'] = oid(fields['_id'])
            camera = deepcopy(sample_camera['data'][0])
            camera.update(fields)
            return camera

        for bootstrap in files.test_files['bootstrap.json']:
            if bootstrap['unifi_video_version'] == bootstrap_version:
                bootstrap_fn = os.path.join(
                    os.path.dirname(__file__), 'files', bootstrap['filename'])

        with open(bootstrap_fn, 'rb') as f:
            bootstrap = json.loads(f.read().decode('utf8'))

        #
        # Init UnifiVideoAPI with empty camera and recording collections
        #
        mocked_urlopen.side_effect = mocked_response(
            arg_pile=[
                {'data': json.dumps(empty_response).encode('utf8')},
                {'data': json.dumps(empty_response).encode('utf8')},
                {'data': json.dumps(bootstrap).encode('utf8')},
            ],
            set_cookies=True)
        uva = UnifiVideoAPI(api_key='****')
        for coll in (uva.cameras, uva.active_cameras, uva.managed_cameras):
            self.assertEqual(len(coll), 0)

        #
        # Load the stages, test count and membership for all three camera
        # collections
        #
        for stage in stages:
            tests = stage.pop()
            mocked_urlopen.side_effect = mocked_response('{}'.encode('utf8'))
            mocked_urlopen.side_effect = mocked_response(
                json.dumps(
                    {'data': list(map(def_camera_data, stage))}).encode('utf8'))
            uva.refresh_cameras()
            for coll_name, expected in tests.items():
                self.assertEqual(
                    len(getattr(uva, coll_name)),
                    len(expected['ids']))
                self.assertEqual(
                    set([oid(i) for i in expected['ids']]),
                    set([cam._id for cam in getattr(uva, coll_name)]))

if __name__ == '__main__':
    unittest.main()
