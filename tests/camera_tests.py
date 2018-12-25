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

responses = {}

with open(os.path.join(os.path.dirname(__file__),
        'files/camera.json'), 'rb') as f:
    responses['camera'] = f.read()


class BasicCameraTests(unittest.TestCase):

    @patch('unifi_video.api.urlopen')
    def test_aa_camera(self, mocked_urlopen):
        """Test UnifiVideoCamera init"""

        test_camera = json.loads(responses['camera'])['data'][0]

        mac_addr = 'fc:ec:da:d8:1c:d1'
        _id = test_camera['_id']
        _name = test_camera['name']
        _model = test_camera['model']
        _platform = test_camera['platform']
        _tag = test_camera['osdSettings']['tag']

        mocked_urlopen.side_effect = mocked_response()

        ufva = UnifiVideoAPI(username='username', password='password',
            addr='0.0.0.0')

        camera = ufva.cameras[_id]

        self.assertEqual(len(ufva.cameras), 1)
        self.assertEqual(camera.mac_addr, mac_addr)
        self.assertEqual(camera._id, _id)
        self.assertEqual(camera.name, _name)
        self.assertEqual(camera.platform, _platform)
        self.assertEqual(camera.model, _model)
        self.assertEqual(camera.overlay_text, _tag)

    @patch('unifi_video.api.urlopen')
    def test_ab_unsupported_camera(self, mocked_urlopen):
        """Init with unsupported camera model"""

        ufva = get_ufva_w_mocked_urlopen(mocked_urlopen)

        data = json.loads(responses['camera'])

        second_camera = deepcopy(data['data'][0])
        second_camera['_id'] = second_camera['_id'].replace('f', 'c')\
            .replace('b', 'c').replace('5', '4')
        second_camera['model'] = 'Some unknown model'

        data['data'].append(second_camera)

        mocked_urlopen.side_effect = mocked_response(json.dumps(data)\
            .encode('utf8'))

        self.assertRaises(CameraModelError, ufva.refresh_cameras)
        self.assertEqual(len(ufva.cameras), 1)
        self.assertIn(data['data'][0]['_id'], ufva.cameras)
        self.assertNotIn(second_camera['_id'], ufva.cameras)

    @patch('unifi_video.api.urlopen')
    def test_ac_simple_ips_actionables(self, mocked_urlopen):
        """Test simple isp actionables"""

        def put_mock(url, camera_data, *args, **kwargs):
            """Pretend unifi_video.api.put"""

            res_data = {'data': []}
            res_data['data'].append(camera_data)
            return res_data

        ufva = get_ufva_w_mocked_urlopen(mocked_urlopen)

        with patch('unifi_video.api.UnifiVideoAPI.put') as put:

            from unifi_video.camera import common_isp_actionables

            put.side_effect = put_mock

            # Since brightness, contrast, hue, saturation, denoise
            # and sharpness are really just the same function, we only
            # need to test one of them: brightness
            isp_method = 'brightness'

            for ispa in common_isp_actionables:
                if ispa[0] == isp_method:
                    brightness_floor = ispa[1]
                    brightness_ceiling = ispa[2]
                    break

            args_and_expected_returns = [

                # Expectation: input values lower than the floor should
                # be transformed to whatever the floor is
                [brightness_floor - 100, brightness_floor],

                # Expectation: input values higher than the ceiling should
                # be transformed to equal the ceiling
                [brightness_ceiling + 100, brightness_ceiling],

                [brightness_ceiling - brightness_floor - 1,
                 brightness_ceiling - brightness_floor - 1],
            ]

            for camera in ufva.cameras:
                isp_callable = getattr(camera, isp_method)
                for each in args_and_expected_returns:
                    arg, ret = each
                    isp_callable(arg)
                    self.assertEqual(isp_callable(), ret)
                break

if __name__ == '__main__':
    unittest.main()
