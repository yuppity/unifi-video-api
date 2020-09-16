import os.path
import random
import json

from unifi_video import UnifiVideoAPI, CameraModelError, \
    UnifiVideoVersionError

try:
    from mock import Mock, patch, MagicMock
except ModuleNotFoundError:
    from unittest.mock import Mock, patch, MagicMock

empty_response = {
    'data': [],
    'meta': {},
}

def mocked_response(data=None, res_json=True, set_cookies=False, arg_pile=[]):

    def response(req):

        args = arg_pile.pop() if len(arg_pile) else {}

        _data = args.get('data', data)
        _res_json = args.get('res_json', res_json)
        _set_cookies = args.get('set_cookies', set_cookies)

        url = req.get_full_url()

        mocked_res = Mock()
        res_data_file = None

        if _data:
            mocked_res.read.return_value = _data

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

        if _res_json:
            mocked_res.headers = {'Content-Type': 'application/json'}

        if _set_cookies == True:
            mocked_res.headers['Set-Cookie'] = 'JSESSIONID_AV={}; ' \
                'Path=/; HttpOnly'.format(
                    ''.join(random.choice('ABCDEF123456789') for i in range(32)))
        elif isinstance(_set_cookies, dict):
            # TODO
            pass


        return mocked_res

    return response

def get_ufva_w_mocked_urlopen(mocked_urlopen, *args, **kwargs):
    mocked_urlopen.side_effect = mocked_response(*args, **kwargs)
    return UnifiVideoAPI(username='username', password='password',
        addr='0.0.0.0')

def read_fp(basename):
    with open(os.path.join(
            os.path.dirname(__file__),
            'files',
            basename), 'r') as f:
        return json.loads(f.read())
