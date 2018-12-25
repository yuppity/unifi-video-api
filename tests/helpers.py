import os.path

from unifi_video import UnifiVideoAPI, CameraModelError, \
    UnifiVideoVersionError

try:
    from mock import Mock, patch, MagicMock
except ModuleNotFoundError:
    from unittest.mock import Mock, patch, MagicMock

def mocked_response(data=None, res_json=True):

    def response(req):
        url = req.get_full_url()

        mocked_res = Mock()
        res_data_file = None

        if data:
            mocked_res.read.return_value = data

        else:
            if 'bootstrap' in url:
                res_data_file = 'files/bootstrap.json'
            elif 'camera' in url:
                res_data_file = 'files/camera.json'
            elif 'recording' in url:
                res_data_file = 'files/recordings.json'
            else:
                raise ValueError('Unknown url: {}'.format(url))

            filename = os.path.join(os.path.dirname(__file__), res_data_file)

            with open(filename, 'rb') as f:
                mocked_res.read.return_value = f.read()

        if res_json:
            mocked_res.headers = {'Content-Type': 'application/json'}

        return mocked_res

    return response

def get_ufva_w_mocked_urlopen(mocked_urlopen, *args, **kwargs):
    mocked_urlopen.side_effect = mocked_response(*args, **kwargs)
    return UnifiVideoAPI(username='username', password='password',
        addr='0.0.0.0')
