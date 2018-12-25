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

from helpers import mocked_response, get_ufva_w_mocked_urlopen
from unifi_video import UnifiVideoAPI, CameraModelError, \
    UnifiVideoVersionError

py3 = sys.version_info[0] == 3

class BasicCameraTests(unittest.TestCase):

    @patch('unifi_video.api.urlopen')
    def test_aa_camera(self, mocked_urlopen):
        """Test UnifiVideoCamera init"""

        mac_addr = 'fc:ec:da:d8:1c:d1'

        mocked_urlopen.side_effect = mocked_response()

        ufva = UnifiVideoAPI(username='username', password='password',
            addr='0.0.0.0')

        camera = ufva.cameras['5bfb35230f12f177788ec2ac']
        self.assertEqual(len(ufva.cameras), 1)
        self.assertEqual(camera.mac_addr, mac_addr)

    @patch('unifi_video.api.urlopen')
    def test_ab_unsupported_camera(self, mocked_urlopen):
        """Init with unsupported camera model"""

        ufva = get_ufva_w_mocked_urlopen(mocked_urlopen)

        with open(os.path.join(os.path.dirname(__file__),
                'files/camera.json'), 'rb') as f:
            data = json.loads(f.read())

        second_camera = deepcopy(data['data'][0])
        second_camera['_id'] = second_camera['_id'].replace('5b', '6c')
        second_camera['model'] = 'Some unknown model'

        data['data'].append(second_camera)

        mocked_urlopen.side_effect = mocked_response(json.dumps(data)\
            .encode('utf8'))

        self.assertRaises(CameraModelError, ufva.refresh_cameras)
        self.assertEqual(len(ufva.cameras), 1)
        self.assertIn(data['data'][0]['_id'], ufva.cameras)
        self.assertNotIn(second_camera['_id'], ufva.cameras)

if __name__ == '__main__':
    unittest.main()
