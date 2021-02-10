from __future__ import print_function, unicode_literals
from functools import wraps
from copy import deepcopy
from datetime import datetime

import time

from .single import UnifiVideoSingle
from . import utils

endpoints = {
    'save': lambda x: 'camera/{}'.format(x),
    'data': lambda x: 'camera/{}'.format(x),
    'snapshot': lambda c, w: 'snapshot/camera/{}?force=true{}'.format(
        c, '&width={}'.format(w) if w else ''),
    'recording_span': lambda x, s, e: 'video/camera?' \
        'startTime={}&endTime={}&cameras[]={}'.format(s, e, x)
}

# Supported camera models, checked during UnifiVideoCamera initialization.
#
# Some model specifications include list of supported features. These are
# not currently checked against and are included only to account for
# some potential future use.
#
# The structure is constructed from bits gleaned from the frontend JS
# served by UniFi Video.
models = {
    'UVC': {},

    'UVC G3': {
        'features': [
            'external_accessory'
        ],
    },

    'UVC G3 Dome': {
        'features': [
            'can_play_sound',
            'toggable_led',
        ],
    },

    'UVC Dome': {},

    'UVC Pro': {
        'pro': True,
        'features': [
            'optical_zoom',
        ],
    },

    'UVC G3 Pro': {
        'pro': True,
        'features': [
            'optical_zoom',
        ],
    },

    'UVC G3 Flex': {
        'features': [
            'can_play_sound',
            'toggable_led',
        ],
    },

    'UVC Micro': {
        'features': [
            'can_play_sound',
            'toggable_led',
        ],
    },

    'UVC G3 Micro': {
        'features': [
            'can_play_sound',
            'toggable_led',
        ],
    },

    'Vision Pro': {
        'features': [
            'can_play_sound',
            'toggable_led',
        ],
    },

    'airCam': {},

    'airCam Dome': {},

    'airCam Mini': {},

    'UVC G4 Bullet': {
        'features': [
        ],
    },

    'UVC G4 Pro': {
        'features': [
            'toggable_led',
            'optical_zoom',
            'animate_led_on_motion',
        ],
    },
}

common_isp_actionables = [
    ['brightness', 0, 100],
    ['contrast', 0, 100],
    ['hue', 0, 100],
    ['saturation', 0, 100],
    ['denoise', 0, 100],
    ['sharpness', 0, 100],
]

def determine_img_actionables(fw_platform, camera_model):
    actionables = list(map(lambda x: x[0], common_isp_actionables))
    actionables.append('orientation')

    if fw_platform == 'GEN1':
        actionables.extend(['gamma', 'aeModeGen1'])
    else:
        actionables.extend(['wdr', 'aeMode'])

    if camera_model in ['UVC Pro', 'UVC G3 Pro']:
        actionables.extend(['irLedModePro', 'zoom', 'focus'])
    else:
        actionables.append('irLedMode')

    return actionables

def isp_actionable(floor=0, ceiling=100, name=None):
    def decfn(fn):
        @wraps(fn)
        def wrapper(camera, val=None):
            fn_name = name or fn.__name__
            if fn_name not in camera._isp_actionables:
                raise CameraModelError('This camera model ({}) has no ' \
                    'support for {} control'.format(camera.model, fn_name))
            if val is None:
                return fn(camera)
            if val > ceiling:
                val = ceiling
            elif val < floor:
                val = floor
            return fn(camera, val)
        return wrapper
    return decfn

def add_actionable(actionable):
    name, floor, ceiling = actionable

    def fn(self, value=None):
        isp = self._data['ispSettings']
        if value is None:
            return isp.get(name, -1)
        isp[name] = value
        self.update(True)
        if isp[name] == value:
            return True
        else:
            return False
    fn.__name__ = str(name)
    fn.__doc__ = """Control image {name}

    Args:
        value (int or NoneType): New {name} value
            (min: ``{floor}``, max: ``{ceiling}``)

    Returns:
        bool or int: ``True`` or ``False``, depending on whether new value
        value was successfully registered. Current {name} value when
        called without input value.

    """.format(name=name, floor=floor, ceiling=ceiling)

    setattr(UnifiVideoCamera, name, isp_actionable(floor, ceiling)(fn))

class CameraModelError(ValueError):
    """Unsupported camera model"""

    def __init__(self, message=None):
        if not message:
            message = 'Unsupported camera model'
        super(CameraModelError, self).__init__(message)

class UnifiVideoCamera(UnifiVideoSingle):
    """Represents a single camera connected to a UniFi Video server
    (:class:`~unifi_video.api.UnifiVideoAPI`).

    Attributes:
        name (str or NoneType):
            Camera name
        uuid (str):
            Camera UUID
        host (str):
            Camera host address
        model (str or NoneType):
            Camera model
        platform (str or NoneType):
            Firmware platform
        overlay_text (str):
            Custom text overlayd over the image
        mac_addr (str):
            Camera MAC address
        utc_h_offset (int or NoneType):
            UTC offset in hours
        state (str):
            Camera state
        managed (bool):
            Whether camera is managed by the UniFi Video instance
        provisioned (bool):
            Whether camera is provisioned
        managed_by_others (bool):
            Whether camera is managed by some other UniFi Video instance
        disconnect_reason (str):
            Reason for most recent disconnect
        connected (bool):
            Whether camera is connected (ie, not disconnected or in process of
            rebooting or being upgraded)
        last_recording_id (str):
            MongoDB ObjectID of latest recording
        last_recording_start_time (int):
            Unix timestamp (in ms): start time of latest recording
        last_seen (int):
            Unix timestamp (in ms). Meaning depends on the value of
            :attr:`UnifiVideoCamera.state`:

                - *CONNECTED*: timestamp for when the camera came online
                - *DISCONNECTED*: timestamp for when the camera went offline
        last_seen_ndt (datetime or NoneType):
            :attr:`UnifiVideoCamera.last_seen` as naive :class:`datetime` object
        _id (str):
            Camera ID (MongoDB ObjectID as hex string)
        _data (dict):
            Complete camera JSON from UniFi Video server
        _isp_actionables (list):
            List of supported image settings

    Warning:
        Attributes having to do with camera state reflect the state
        as it was during object instantiation.

    Warning:
        :attr:`UnifiVideoCamera.last_seen` changes were observed on
        UniFi Video v3.10.13. No attempt has been made to verify
        :attr:`UnifiVideoCamera.last_seen` acts the same way across
        all supported UniFi Video versions.
    """

    def _load_data(self, data):

        self.model = data.get('model', None)

        if not self.model or self.model not in models:
            raise CameraModelError

        self._data = data
        self._id = data['_id']
        self.name = data.get('name', None)
        self.uuid = data.get('uuid', '')
        self.host = data.get('host', '')
        self.platform = data.get('platform', None)
        self.overlay_text = data.get('osdSettings', {}).get('tag', None)
        self.mac_addr = utils.format_mac_addr(data.get('mac', 'ffffffffffff'))
        self._isp_actionables = determine_img_actionables(self.platform,
            self.model)
        self.state = data.get('state', '')
        self.managed = data.get('managed', None)
        self.provisioned = data.get('provisioned', None)
        self.managed_by_others = data.get('managedByOthers', None)
        self.disconnect_reason = data.get('disconnectReason') or ''
        self.connected = self.state == 'CONNECTED'
        self.last_recording_id = data.get('lastRecordingId', '') or ''
        self.last_recording_start_time = \
            data.get('lastRecordingStartTime', 0) or 0
        self.last_seen = data.get('lastSeen', 0)
        self.last_seen_ndt = datetime.fromtimestamp(self.last_seen / 1000) \
            if self.last_seen else None

        try:
            self.utc_offset = utils.parse_gmt_offset(
                (data.get('deviceSettings') or {}).get('timezone', ''))
            self.utc_h_offset = self.utc_offset / 3600
        except (TypeError, ValueError):
            self.utc_offset = None
            self.utc_h_offset = None

    def _simple_isp_actionable(self, setting_name, value):
        isp = self._data['ispSettings']
        if value is None:
            return isp.get(setting_name, -1)
        isp[setting_name] = value
        self.update(True)
        if isp[setting_name] == value:
            return True
        else:
            return False

    def _toggable_osd_actionable(self, setting_name, enabled, ints=False):
        osd = self._data['osdSettings']
        if enabled is None:
            return bool(osd[setting_name])
        osd[setting_name] = int(enabled) if ints else enabled
        self.update(True)
        if osd[setting_name] == enabled:
            return True
        else:
            return False

    def update(self, save=False):
        """Update settings from remote UniFi Video server (``self._api``).
        Call with ``True`` to write local settings to remote before updating.

        :param bool save: Whether to push settings to the camera
        """

        if save:
            self._load_data(self._extract_data(
                self._api.put(endpoints['save'](self._id), self._data)))
        else:
            self._load_data(self._extract_data(
                self._api.get(endpoints['data'](self._id))))

    def snapshot(self, filename=None, width=0):
        """Take and download snapshot.

        :param filename: Filename to save the snapshot to
        :type filename: str or None
        :param width: Image width in pixels
        :type width: int
        """

        return self._api.get(
            endpoints['snapshot'](self._id, int(width)),
            filename if filename else 'snapshot-{}-{}.jpg'.format(
                self._id, int(time.time())))

    def recording_between(self, start_time, end_time, filename=None):
        '''Download a recording of the camera's footage from an arbitrary
        timespan, between ``start_time`` and ``end_time``.

        Arguments:
            start_time (datetime or str or int):
                Recording start time. (See
                :meth:`~unifi_video.utils.dt_resolvable_to_ms`.)
            end_time (datetime or str or int):
                Recording end time. (See
                :meth:`~unifi_video.utils.dt_resolvable_to_ms`.)
            filename (str, optional):
                Filename to save the recording to (a ZIP file).
                Will use whatever the server provides if left out.

        Tip:
            Widen the time span by a few seconds at each end. UniFi Video often
            falls a little short of the exact start and end times.
        '''

        start_time = utils.dt_resolvable_to_ms(
            start_time,
            utc_offset=self._api.utc_offset,
            resolution=1000)
        end_time = utils.dt_resolvable_to_ms(
            end_time,
            utc_offset=self._api.utc_offset,
            resolution=1000)

        return self._api.get(endpoints['recording_span'](
            self._id, start_time, end_time), filename if filename else '')

    @isp_actionable(0, 3, name='wdr')
    def dynamic_range(self, wdr=None):
        """Control image WDR (dynamic range). Input should be either `None`
        or an `int` between ``0`` and ``3``.

        :param wdr: New WDR value
        :type wdr: int or None

        :return: If value provided: `True` or `False`, depending on
            whether new value was registered. If no value provided: current
            WDR value.

        :rtype: `bool` or `int`
        """

        return self._simple_isp_actionable('wdr', wdr)

    def ir_leds(self, led_state=None):
        """Control IR leds.

        :param led_state: New led state (``auto``, ``on``, or ``off``).
        :type led_state: str or None
        :return: `True` or `False` depending on successful value change.
            Current led state if called with no args.
        :rtype: `bool` or `str`
        """

        isp = self._data['ispSettings']

        if not led_state:
            _s = isp['irLedMode']
            _v = isp['irLedLevel']
            if _s == 'auto':
                return _s
            elif _s == 'manual' and _v == 0:
                return 'off'
            elif _s == 'manual' and _v == 215:
                return 'on'

        isp['irLedLevel'] = 215
        if led_state == 'auto':
            isp['irLedMode'] = 'auto'
        elif led_state == 'on':
            isp['irLedMode'] = 'manual'
        elif led_state == 'off':
            isp['irLedMode'] = 'manual'
            isp['irLedLevel'] = 0
        else:
            raise ValueError('Unknown led_state: {}'.format(led_state))

        verify = isp['irLedMode'] + str(isp['irLedLevel'])
        self.update(True)

        if isp['irLedMode'] + str(isp['irLedLevel']) == verify:
            return True
        else:
            return False

    def onscreen_text(self, text=None):
        """Set or get on-screen text.

        :param text: New on-screen text
        :type text: str or None
        :return: `True` for successful value change, `Fail` for failed
            attempt, current `str` value if called without ``text``.
        :rtype: `bool` or `str`
        """

        if not text:
            return self.overlay_text

        osd = self._data['osdSettings']
        osd['overrideMessage'] = True
        osd['tag'] = text.strip()

        self.update(True)

        if osd['tag'] == text:
            return True
        else:
            return False

    def onscreen_timestamp(self, enabled=None):
        """Set or get on-screen timestamp state.

        :param enabled: New state
        :type enabled: bool or None
        :return: `True` for successful state change, `Fail` for failed
            attempt. Either of the two for current state (when called
            without the ``enabled`` arg)
        :rtype: `bool`
        """

        return self._toggable_osd_actionable('enableDate', enabled, True)

    def onscreen_watermark(self, enabled=None):
        """Enable or disable on-screen watermark. Call without args to get
        current setting.

        :param enabled: Enable or disable
        :type enabled: bool or None
        :return: `True` for successful change, `Fail` for failed attempt.
            One or the other for calls without args.
        :rtype: `bool`
        """

        return self._toggable_osd_actionable('enableLogo', enabled, True)

    def set_recording_settings(self, recording_mode=None, pre_padding_secs=None,
            post_padding_secs=None):
        """Set recording mode and pre/post padding.

        Possible recording modes:
            - ``disable``: don't record
            - ``fulltime``: record at all times
            - ``motion``: record when motion detected

        :param str recording_mode: See above
        :param int pre_padding_secs: Number of seconds to include
            pre-motion footage of
        :param int post_padding_secs: Number of seconds to include
            post-motion footage of
        """

        rec_settings = self._data['recordingSettings']

        if recording_mode:
            if recording_mode == 'disable':
                rec_settings['fullTimeRecordEnabled'] = False
                rec_settings['motionRecordEnabled'] = False
            elif recording_mode == 'fulltime':
                rec_settings['fullTimeRecordEnabled'] = True
                rec_settings['motionRecordEnabled'] = True
            elif recording_mode == 'motion':
                rec_settings['fullTimeRecordEnabled'] = False
                rec_settings['motionRecordEnabled'] = True
            else:
                raise ValueError('Unknow recording mode "{}"'.format(
                    recording_mode))

        if pre_padding_secs is not None:
            rec_settings['prePaddingSecs'] = pre_padding_secs

        if post_padding_secs is not None:
            rec_settings['postPaddingSecs'] = post_padding_secs

        verify = deepcopy(rec_settings)
        self.update(True)
        return verify == self._data['recordingSettings']

    def get_recording_settings(self, all=False):
        """Get camera's recording settings

        Arguments:
            all (bool): Whether to show all available settings. The default
                is to only show the settings that are controllable by calling
                :func:`~unifi_video.camera.UnifiVideoCamera.set_recording_settings`.
        """

        controllable = [
            'motionRecordEnabled',
            'fullTimeRecordEnabled',
            'prePaddingSecs',
            'postPaddingSecs',
        ]

        all_settings = self._data.get('recordingSettings', {})

        return {k: all_settings.get(k, None) for k in controllable} \
            if not all else all_settings

    def __str__(self):
        _filter = ['name', 'model', 'platform']
        return '{}: {}'.format(
            type(self).__name__,
            {k: v for k, v in self.__dict__.items() if k in _filter})

# Define methods for controlling the isp actionables that are common to all
# camera models. Other actionables -- those not common to all models --
# are controlled with methods defined in UnifiVideoCamera body.
#
# Note: "isp actionables" is what the Ubiquiti provided frontend JS refers
# to contrast, brightness, saturation, etc. as.
for actionable in common_isp_actionables:
    add_actionable(actionable)
