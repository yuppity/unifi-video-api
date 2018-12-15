from __future__ import print_function, unicode_literals

try:
    from urllib.parse import urljoin
except ImportError:
    from urlparse import urljoin

try:
    from urllib.request import urlopen, Request
    from urllib.error import HTTPError
except ImportError:
    from urllib2 import urlopen, Request, HTTPError

import json
import time

from .camera import UnifiVideoCamera

try:
    type(unicode)
except NameError:
    unicode = str


RECORDINGS_CACHE_EXPIRY = 60 * 2

endpoints = {
    'login': 'login',
    'cameras': 'camera',
}

class UnifiVideoAPI(object):

    def __init__(self, username, password, addr, port=7080, schema='http'):
        self.login_attempts = 0
        self.jsession_av = None
        self.username = username
        self.password = password
        self.base_url = '{}://{}:{}/api/2.0/'.format(schema, addr, port)
        self.cameras = set()
        self._init_cameras()

        self.nvr_recordings = {
            'last_update': int(time.time()),
            'recordings': [],
        }

    def _init_cameras(self):
        camera_data = self.get(endpoints['cameras'])

        if isinstance(camera_data, dict):
            for camera in camera_data.get('data', []):
                self.cameras.add(UnifiVideoCamera(self, camera))

        for c in self.cameras:
            print(c._id)

    def _ensure_headers(self, req):
        req.add_header('Content-Type', 'application/json')
        if self.jsession_av:
            req.add_header('Cookie', 'JSESSIONID_AV={}'\
                .format(self.jsession_av))

    def _build_req(self, url, data=None, method=None):
        url = urljoin(self.base_url, url)
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

    def _get_response_content(self, res, raw=False):
        try:
            if res.headers['Content-Type'] == 'application/json':
                return json.loads(res.read().decode('utf8'))
            raise KeyError
        except KeyError:
            if isinstance(raw, str) or isinstance(raw, unicode):
                with open(raw, 'wb') as f:
                    while True:
                        chunk = res.read(4096)
                        if not chunk:
                            break
                        f.write(chunk)
                    return True
            elif isinstance(raw, bool):
                return res.read()
            else:
                try:
                    return res.read().decode('utf8')
                except UnicodeDecodeError:
                    return res.read()

    def get(self, url, raw=False):
        req = self._build_req(url)
        try:
            res = urlopen(req)
            self._parse_cookies(res)
            return self._get_response_content(res, raw)
        except HTTPError as err:
            if err.code == 401 and self.login_attempts == 0:
                if self.login():
                    return self.get(url, raw)
            return False

    def post(self, url, data=None, raw=False, method=None):
        if data:
            req = self._build_req(url, data, method)
        else:
            req = self._build_req(url, method)
        try:
            res = urlopen(req)
            self._parse_cookies(res)
            return self._get_response_content(res, raw)
        except HTTPError as err:
            if err.code == 401 and url != 'login' and self.login_attempts == 0:
                if self.login():
                    return self.post(url, data, raw)
            return False

    def put(self, url, data=None, raw=False):
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

__all__ = ['UnifiVideoAPI']
