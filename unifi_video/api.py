from __future__ import print_function, unicode_literals

try:
    from urllib.parse import urljoin, urlparse, urlunparse
except ImportError:
    from urlparse import urljoin, urlparse, urlunparse

try:
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import urlopen, Request, HTTPError

import json

from .camera import UnifiVideoCamera
from .recording import UnifiVideoRecording

try:
    type(unicode)
except NameError:
    unicode = str


RECORDINGS_CACHE_EXPIRY = 60 * 2

endpoints = {
    'login': 'login',
    'cameras': 'camera',
    'recordings': lambda x: 'recording?idsOnly=false&' \
        'sortBy=startTime&sort=desc&limit={}'.format(x),
}

class UnifiVideoAPI(object):

    def __init__(self, api_key=None, username=None, password=None,
            addr='localhost', port=7080, schema='http', verify_cert=True):

        if not verify_cert and schema == 'https':
            import ssl
            self._ssl_context = ssl._create_unverified_context()

        if not api_key and not (username and password):
            raise ValueError('To init {}, provide either API key ' \
                'or username password pair'.format(type(self).__name__))

        self.api_key = api_key
        self.login_attempts = 0
        self.jsession_av = None
        self.username = username
        self.password = password
        self.base_url = '{}://{}:{}/api/2.0/'.format(schema, addr, port)

        self.cameras = set()
        self.recordings = set()
        self.refresh_cameras()
        self.refresh_recordings()

    def refresh_cameras(self):
        cameras = self.get(endpoints['cameras'])
        if isinstance(cameras, dict):
            for camera in cameras.get('data', []):
                self.cameras.add(UnifiVideoCamera(self, camera))

    def refresh_recordings(self, limit=300):
        recordings = self.get(endpoints['recordings'](limit))
        if isinstance(recordings, dict):
            for recording in recordings.get('data', []):
                self.recordings.add(UnifiVideoRecording(self, recording))

    def _ensure_headers(self, req):
        req.add_header('Content-Type', 'application/json')
        if self.jsession_av:
            req.add_header('Cookie', 'JSESSIONID_AV={}'\
                .format(self.jsession_av))

    def _build_req(self, url, data=None, method=None):
        url = urljoin(self.base_url, url)
        if self.api_key:
            _s, _nloc, _path, _params, _q, _f = urlparse(url)
            _q = '{}&apiKey={}'.format(_q, self.api_key) if len(_q) \
                else 'apiKey={}'.format(self.api_key)
            url = urlunparse((_s, _nloc, _path, _params, _q, _f))
        req = Request(url, bytes(json.dumps(data).encode('utf8'))) \
            if data else Request(url)
        self._ensure_headers(req)
        if method:
            req.get_method = lambda: 'PUT'
        return req

    def _parse_cookies(self, res, return_existing=False):
        if 'Set-Cookie' not in res.headers:
            return False
        cookies = res.headers['Set-Cookie'].split(',')
        for cookie in cookies:
            for part in cookie.split(';'):
                if 'JSESSIONID_AV' in part:
                    self.jsession_av = part\
                        .replace('JSESSIONID_AV=', '').strip()
                    return True

    def _urlopen(self, req):
        try:
            return urlopen(req, context=self._ssl_context)
        except AttributeError:
            return urlopen(req)

    def _get_response_content(self, res, raw=False):
        try:
            if res.headers['Content-Type'] == 'application/json':
                return json.loads(res.read().decode('utf8'))
            raise KeyError
        except KeyError:
            upstream_filename = None

            if 'Content-Disposition' in res.headers:
                for part in res.headers['Content-Disposition'].split(';'):
                    part = part.strip()
                    if part.startswith('filename='):
                        upstream_filename = part.split('filename=').pop()

            if isinstance(raw, str) or isinstance(raw, unicode):
                filename = raw if len(raw) else upstream_filename
                with open(filename, 'wb') as f:
                    while True:
                        chunk = res.read(4096)
                        if not chunk:
                            break
                        f.write(chunk)
                    f.truncate()
                    return True
            elif isinstance(raw, bool):
                return res.read()
            else:
                try:
                    return res.read().decode('utf8')
                except UnicodeDecodeError:
                    return res.read()

    def _handle_http_401(self, url, raw):
        if self.api_key:
            raise ValueError('Invalid API key')
        elif self.login():
            return self.get(url, raw)

    def get(self, url, raw=False):
        req = self._build_req(url)
        try:
            res = self._urlopen(req)
            self._parse_cookies(res)
            return self._get_response_content(res, raw)
        except HTTPError as err:
            if err.code == 401 and self.login_attempts == 0:
                return self._handle_http_401(url, raw)
            return False

    def post(self, url, data=None, raw=False, method=None):
        if data:
            req = self._build_req(url, data, method)
        else:
            req = self._build_req(url, method)
        try:
            res = self._urlopen(req)
            self._parse_cookies(res)
            return self._get_response_content(res, raw)
        except HTTPError as err:
            if err.code == 401 and url != 'login' and self.login_attempts == 0:
                return self._handle_http_401(url, raw)
            return False

    def put(self, url, data=None, raw=False):
        if self.api_key:
            url += '&apiKey={}'.format(self.api_key)
        return self.post(url, data, raw, 'PUT')

    def login(self):
        self.login_attempts = 1
        res_data = self.post(endpoints['login'], {
            'username': self.username,
            'password': self.password})
        if res_data:
            self.login_attempts = 0
            return True
        else:
            return False

    def get_camera(self, search_term):
        search_term = search_term.lower()
        for camera in self.cameras:
            if camera._id == search_term or \
                    camera.name.lower() == search_term or \
                    camera.overlay_text.lower() == search_term:
                return camera

    def get_recording(self, rec_id):
        for rec in self.recordings:
            if rec._id == rec_id:
                return rec

__all__ = ['UnifiVideoAPI']
