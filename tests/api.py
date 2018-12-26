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

from helpers import mocked_response, get_ufva_w_mocked_urlopen
from unifi_video import UnifiVideoAPI, CameraModelError, \
    UnifiVideoVersionError

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
    def test_aa_api_init(self, mocked_urlopen):
        """Test API init

        UnifiVideoAPI should:
          - throw ValueError when called without usermame-password pair
            or API key
          - throw UnifiVideoVersionError when check_ufv_version == True
            and GET bootstrap response has an unknown version string
        """

        self.assertRaises(ValueError, UnifiVideoAPI)

        res_w_unk_ufv_ver = json.loads(responses['bootstrap'])
        res_w_unk_ufv_ver['data'][0]['systemInfo']['version'] = 'qwerty'

        mocked_urlopen.side_effect = mocked_response(json.dumps(
            res_w_unk_ufv_ver).encode('utf8'), set_cookies=True)

        self.assertRaises(UnifiVideoVersionError, UnifiVideoAPI,
            api_key='xxxxxx')

        mocked_urlopen.side_effect = mocked_response(arg_pile=[
            {'data': responses['recordings']},
            {'data': responses['camera']},
            {'data': json.dumps(res_w_unk_ufv_ver).encode('utf8')},
        ])

        self.assertIsInstance(UnifiVideoAPI(api_key='xxxxx',
            check_ufv_version=False), UnifiVideoAPI)

if __name__ == '__main__':
    unittest.main()
