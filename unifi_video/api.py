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
from .collections import UnifiVideoCollection
from .utils import parse_gmt_offset, dt_resolvable_to_ms

from distutils.version import LooseVersion

try:
    type(unicode)
except NameError:
    unicode = str

endpoints = {
    'login': 'login',
    'cameras': 'camera',
    'recordings': lambda x: 'recording?idsOnly=false&' \
        'sortBy=startTime&sort=desc&limit={}'.format(x) \
        if x is not None else 'recording',
    'recording': lambda x: 'recording/{}'.format(
        x._id if isinstance(x, UnifiVideoRecording) else x),
    'bootstrap': 'bootstrap',
    'delete_all': 'recording?deleteRecordings&confirmed=true',
}

class UnifiVideoVersionError(ValueError):
    """Unsupported UniFi Video version"""

    def __init__(self, message=None):
        if not message:
            message = 'Unsupported UniFi Video version'
        super(UnifiVideoVersionError, self).__init__(message)

class UnifiVideoHTTPError(ValueError):
    """HTTP error with message from UniFi Video server"""

    def __init__(self, code=None, message=None, caused_by=None):
        msg = 'HTTP {} from UniFi Video.'.format(code)
        if message:
            msg += ' Error: {}.'.format(message)
        if caused_by:
            msg += ' Caused by: {}'.format(caused_by)
        super(UnifiVideoHTTPError, self).__init__(msg)

class UnifiVideoAPI(object):
    """Encapsulates a single UniFi Video server.

    Arguments:
        api_key (str): UniFi Video API key
        username (str): UniFi Video account username
        password (str): UniFi Video account pasword
        addr (str): UniFi Video host address
        port (int): UniFi Video host port
        schema (str): Protocol schema to use. Valid values: `http`, `https`
        verify_cert (bool): Whether to verify UniFi Video's TLS cert when
            connecting over HTTPS
        check_ufv_version (bool): Set to ``False`` to use with untested
            UniFi Video versions
        utc_offset_sec (int or NoneType): UniFi Video server's UTC offset
            in seconds.

    Note:

        At minimum, you have to

        - provide either an API key or a username:password pair
        - set the host address and port to wherever your UniFi Video
          is listening at

    Attributes:
        _data (dict): UniFi Video "bootstrap" JSON as a dict
        base_url (str): API base URL
        api_key (str or NoneType): API key (from input params)
        username (str or NoneType): Username (from input params)
        password (str or NoneType): Password (from input params)
        name (str or NoneType): UniFi Video server name
        version (str or NoneType): UniFi Video version
        jsession_av (str or NoneType): UniFi Video session ID

        cameras (:class:`UnifiVideoCollection`):
            Collection of :class:`~unifi_video.camera.UnifiVideoCamera`
            objects. Includes all cameras that the associated UniFi Video
            instance is aware of

        active_cameras (:class:`UnifiVideoCollection`):
            Like :attr:`UnifiVideoAPI.cameras` but only includes cameras
            that are both connected and managed by the UniFi Video instance.

        managed_cameras (:class:`UnifiVideoCollection`):
            Includes all cameras that are managed by the UniFi Video instance,
            whether they're online or not.

        recordings (:class:`UnifiVideoCollection`):
            Collection of :class:`~unifi_video.recording.UnifiVideoRecording`
            objects
    """

    _supported_ufv_versions = []
    _supported_ufv_version_ranges = [
        ['3.9.12', '3.10.13'],
    ]

    def __init__(self, api_key=None, username=None, password=None,
            addr='localhost', port=7080, schema='http', verify_cert=True,
            check_ufv_version=True, utc_offset_sec=None):

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
        self.utc_offset = utc_offset_sec
        self.base_url = '{}://{}:{}/api/2.0/'.format(schema, addr, port)
        self._version_stickler = check_ufv_version

        self._load_data(self.get(endpoints['bootstrap']))

        self.cameras = UnifiVideoCollection(UnifiVideoCamera)
        self.active_cameras = UnifiVideoCollection(UnifiVideoCamera)
        self.managed_cameras = UnifiVideoCollection(UnifiVideoCamera)
        self.recordings = UnifiVideoCollection(UnifiVideoRecording)
        self.refresh_cameras()
        self.refresh_recordings()

        # /bootstrap: data[0].settings.systemSettings.gmtOffset first appeared
        # in version 3.10.2. For earlier versions, try to determine the offset
        # by comparing what is reported by attached cameras. If all cameras
        # report the same offset, use that offset for the server as well
        if self.utc_offset is None:
            camera_utc_offsets = set([
                c.utc_offset for c in self.active_cameras
                if c.utc_offset is not None])
            if len(camera_utc_offsets) == 1:
                self.utc_offset = camera_utc_offsets.pop()

    def _load_data(self, data):
        if not isinstance(data, dict):
            raise ValueError('Server responded with unknown bootstrap data')
        self._data = data.get('data', [{}])
        self.name = self._data[0].get('nvrName', None)
        self.version = self._data[0].get('systemInfo', {}).get('version', None)

        self._is_supported = False

        if self.utc_offset is None:
            system_settings = \
                self._data[0].get('settings', {}).get('systemSettings', {}) \
                    or self._data[0].get('servers', [{}])[0]\
                        .get('systemSettings', {})
            try:
                self.utc_offset = parse_gmt_offset(
                    system_settings.get('gmtOffset', ''))
            except (TypeError, ValueError):
                pass

        if self.version in UnifiVideoAPI._supported_ufv_versions:
            self._is_supported = True
        else:
            v_actual = LooseVersion(self.version)
            for curr_version in UnifiVideoAPI._supported_ufv_version_ranges:
                v_low = LooseVersion(curr_version[0])
                v_high = LooseVersion(curr_version[1])
                try:
                    if v_actual >= v_low and v_actual <= v_high:
                        self._is_supported = True
                        break
                except TypeError as e:
                    break

        if self._version_stickler and not self._is_supported:
            raise UnifiVideoVersionError()

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
            req.get_method = lambda: method
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
        if hasattr(self, '_ssl_context'):
            return urlopen(req, context=self._ssl_context)
        else:
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

    def get(self, url, raw=False, url_params={}):
        """Send GET request.

        Arguments:
            url (str):
                API endpoint (relative to the API base URL)
            raw (str or bool, optional):
                Set `str` filename if you want to save the response to a file.
                Set to ``True``  if you want the to return raw response data.
            url_params (dict, optional):
                URL parameters as a dict. Gets turned into query string and
                appended to ``url``

        Returns:
            Response JSON (as `dict`) when `Content-Type` response header is
            `application/json`

            ``True`` if ``raw`` is `str` (filename) and a file was
            successfully written to

            Raw response body (as `bytes`) if the `raw` input param is of type
            `bool`

            ``False`` on HTTP 4xx - 5xx

        :rtype: NoneType, bool, dict, bytes
        """

        if url_params:
            url = '{}?{}'.format(
                url, UnifiVideoAPI.params_to_query_str(url_params))

        req = self._build_req(url)
        try:
            res = self._urlopen(req)
            self._parse_cookies(res)
            return self._get_response_content(res, raw)
        except HTTPError as err:
            if err.code == 401 and self.login_attempts == 0:
                return self._handle_http_401(url, raw)
            elif err.code == 400 and hasattr(err, 'headers') \
                    and 'application/json' in err.headers.get(
                        'content-type', ''):
                err_body = json.loads(err.read().decode('utf8'))
                if isinstance(err_body, dict) and err_body.get('rc') == 'error':
                    raise UnifiVideoHTTPError(
                        code=err.code,
                        message=err_body.get('message'),
                        caused_by=err_body.get('causedBy'))
            return False

    def post(self, url, data=None, raw=False, _method=None):
        """Send POST request.

        Args:
            url (str): API endpoint (relative to the API base URL)
            data (dict or NoneType): Request body
            raw (str or bool): Filename (`str`) if you want the response
                saved to a file, ``True`` (`bool`) if you want the response
                body as return value

        Returns:
            See :func:`~unifi_video.api.get`.

        """

        if data:
            req = self._build_req(url, data, _method)
        else:
            req = self._build_req(url, method=_method)
        try:
            res = self._urlopen(req)
            self._parse_cookies(res)
            return self._get_response_content(res, raw)
        except HTTPError as err:
            if err.code == 401 and url != 'login' and self.login_attempts == 0:
                return self._handle_http_401(url, raw)
            return False

    def put(self, url, data=None, raw=False):
        """Send PUT request.

        Thin wrapper around :func:`~unifi_video.api.post`; the
        same parameter/return semantics apply here.
        """

        return self.post(url, data, raw, 'PUT')

    def delete(self, url, data=None, raw=False):
        """Send DELETE request.

        Thin wrapper around :func:`~unifi_video.api.post`; the
        same parameter/return semantics apply here.
        """

        return self.post(url, data, raw, 'DELETE')

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

    def refresh_cameras(self):
        '''GET cameras from the server and update camera collections

        Touches :attr:`UnifiVideoAPI.cameras`,
        :attr:`UnifiVideoAPI.active_cameras`, and
        :attr:`UnifiVideoAPI.managed_cameras`
        '''

        collections = {
            'cameras': {
                'new_ids': set(),
                'accepts': lambda _: True,
            },
            'active_cameras': {
                'new_ids': set(),
                'accepts': lambda cam: cam.managed and cam.connected,
            },
            'managed_cameras': {
                'new_ids': set(),
                'accepts': lambda cam: cam.managed,
            },
        }

        # Suspicion: the type check provides zero value and exists simply due
        # to some momentary lapse in coherence at the time it was originally
        # written. Leaving it be, on the off chance that there was a good
        # reason for it. Unable to investigate atm.
        cameras = self.get(endpoints['cameras'])
        if not isinstance(cameras, dict):
            return

        for camera in (
                UnifiVideoCamera(self, c) for c in cameras.get('data', [])):
            for cname, collection in collections.items():
                if collection['accepts'](camera):
                    getattr(self, cname).add(camera)
                    collection['new_ids'].add(camera._id)

        for cname in collections.keys():
            for camera_id in list(getattr(self, cname).keys()):
                if camera_id not in collections[cname]['new_ids']:
                    del getattr(self, cname)[camera_id]

    def refresh_recordings(self, limit=300):
        """GET recordings from the server and update ``self.recordings``.

        :param int limit: Limit the number of recording items
            to fetch (``0`` for no limit).
        """

        for recording in self.get_recordings(
                rec_type='all', order='desc', limit=limit):
            self.recordings.add(recording)

    def get_camera(self, search_term, managed_only=False):
        '''Get camera by its ObjectID, name or overlay text

        Arguments:
            search_term (str):
                String to test against
                :attr:`~unifi_video.UnifiVideoCamera.name`,
                :attr:`~unifi_video.UnifiVideoCamera._id`, and
                :attr:`~unifi_video.UnifiVideoCamera.overlay_text`.

            managed_only (bool):
                Whether to search unmanaged cameras as well.

        Returns:
            :class:`~unifi_video.camera.UnifiVideoCamera` or `NoneType`
            depending on whether or not `search_term` was matched to a camera.

        Tip:
            Do not attempt to find an unmanaged camera by it's overlay text;
            UniFi Video provides limited detail for unmanaged cameras.

        '''

        search_term = search_term.lower()
        for camera in self.cameras:
            is_match = camera._id == search_term or \
                    camera.name.lower() == search_term or \
                    camera.overlay_text.lower() == search_term
            if is_match and (not managed_only or camera.managed):
                return camera

    def get_recordings(self, rec_type='all', camera=None, start_time=None,
            end_time=None, limit=0, order='desc', req_each=False):
        '''Fetch recording listing

        Args:
            rec_type (str, optional):
                Type of recordings to fetch: *all*, *motion* or *fulltime*

            camera (:class:`~unifi_video.camera.UnifiVideoCamera` or str or \
                    list of :class:`~unifi_video.camera.UnifiVideoCamera` or \
                    list of str, optional):
                Camera or cameras whose recordings to fetch

            start_time (datetime or str or int, optional):
                Recording start time. (See
                :meth:`~unifi_video.utils.dt_resolvable_to_ms`.)

            end_time (datetime or str or int, optional):
                Recording end time. (See
                :meth:`~unifi_video.utils.dt_resolvable_to_ms`.)

            order (str, optional):
                Sort order: *desc* or *asc*. Recordings are sorted by their
                start time.

            limit (int, optional):
                Limit the number of recordings

            req_each (bool, optional):
                Whether to save bandwidth on the initial request and to fetch
                each recordings' details individually or to ask for each
                recordings' details to be included in the one and only initial
                request. ``True`` can potentially save you in total bytes
                transferred but will cost you in the number of HTTP requests
                made.

        Returns:
            Iterable[:class:`~unifi_video.recording.UnifiVideoRecording`]

        Note:
            You can use naive :class:`~datetime.datetime` objects or strings
            when you want to mark time in the UniFi Server's local time.
            Otherwise, use Unix timestamps (*int*, **in seconds**) or timezone
            aware :class:`~datetime.datetime` objects.
        '''

        rec_types = {
            'motion': ('motionRecording',),
            'fulltime': ('fullTimeRecording',),
            'all': ('motionRecording', 'fullTimeRecording'),
        }

        url_params = {
            'sortBy': 'startTime',
            'order': order,
            'idsOnly': req_each,
            'limit': limit if limit else None,
            'cause': rec_types[rec_type],
            'startTime': dt_resolvable_to_ms(
                start_time,
                utc_offset=self.utc_offset,
                resolution=1000) if start_time else None,
            'endTime': dt_resolvable_to_ms(
                end_time,
                utc_offset=self.utc_offset,
                resolution=1000) if end_time else None,
            'cameras': camera if isinstance(camera, (list, tuple)) else [camera],
        }

        if req_each:
            return (
                UnifiVideoRecording(
                    self,
                    self.get(endpoints['recording'](rec_id))['data'][0])
                for rec_id in self.get(
                    endpoints['recordings'](None),
                    url_params=url_params)['data']
            )
        else:
            return (
                UnifiVideoRecording(self, rec)
                for rec in self.get(
                    endpoints['recordings'](None),
                    url_params=url_params)['data']
            )

    def delete_all_recordings(self):
        """ Delete all existing recordings """

        return self.delete(endpoints['delete_all'])

    def __str__(self):
        return '{}: {}'.format(type(self).__name__, {
            'name': self.name,
            'version': self.version,
            'supported_version': self._is_supported
        })

    @staticmethod
    def params_to_query_str(params_dict):
        '''Build query string from dict of URL parameters

        Arguments:
            params_dict (dict):
                URL parameters

        Returns:
            str: Query string
        '''

        str_conversions = {
            str: lambda x: x,
            unicode: lambda x: x,
            int: lambda x: '{}'.format(x),
            float: lambda x: '{}'.format(x),
            bool: lambda x: 'true' if x else 'false',
            UnifiVideoCamera: lambda x: x._id,
        }

        params = []
        for k, v in ((k, v) for k, v in params_dict.items() if v is not None):
            if isinstance(v, (list, tuple)):
                for lv in (x for x in v if x is not None):
                    params.append('{}[]={}'.format(
                        k, str_conversions[type(lv)](lv)))
            else:
                params.append('{}={}'.format(k, str_conversions[type(v)](v)))

        return '&'.join(params)

__all__ = ['UnifiVideoAPI']
