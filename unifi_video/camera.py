from __future__ import print_function, unicode_literals
from functools import wraps
from copy import deepcopy

import time

from .single import UnifiVideoSingle
from . import utils

endpoints = {
    'save': lambda x: 'camera/{}'.format(x),
    'data': lambda x: 'camera/{}'.format(x),
    'snapshot': lambda x: 'snapshot/camera/{}?force=true'.format(x),
    'recording_span': lambda x, s, e: 'video/camera?' \
        'startTime={}&endTime={}&cameras[]={}'.format(s, e, x)
}

models = {
    'UVC': {},

    'UVC G3': {
        'features': [
            'external_accessory'
        ]
    },

    'UVC G3 Dome': {
        'features': [
            'can_play_sound', 'toggable_led'
        ]
    },

    'UVC Dome': {},

    'UVC Pro': {
        'pro': True,
        'features': [
            'optical_zoom'
        ]
    },

    'UVC G3 Pro': {
        'pro': True,
        'features': [
            'optical_zoom'
        ]
    },

    'UVC G3 Flex': {
        'features': [
            'can_play_sound', 'toggable_led'
        ]
    },

    'UVC Micro': {
        'features': [
            'can_play_sound', 'toggable_led'
        ]
    },

    'UVC G3 Micro': {
        'features': [
            'can_play_sound', 'toggable_led'
        ]
    },

    'Vision Pro': {
        'features': [
            'can_play_sound', 'toggable_led'
        ]
    },

    'airCam': {},

    'airCam Dome': {},

    'airCam Mini': {},
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
            if val == None:
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
        if value == None:
            return isp.get(name, -1)
        isp[name] = value
        self.update(True)
        if isp[name] == value:
            return True
        else:
            return False
    fn.__name__ = str(name)
    fn.__doc__ =  """Control image {}

    :param value: New {} value
    :type value: int or None

    :return: If value provided: `True` or `False`, depending on
        whether new value was registered. If no value provided: current
        {} value.

    :rtype: `bool` or `int`

    """.format(name, name, name)


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

    :ivar name: Camera name
    :vartype name: str or None

    :ivar model: Camera model
    :vartype model: str or None

    :ivar platform: Firmware platform
    :vartype platform: str or None

    :ivar str overlay_text: Custom text overlayed over the image
    :ivar str mac_addr: Camera's MAC address
    :ivar str _id: Camera's ID on the UniFi Video server it is attached to
    :ivar dict _data: Complete copy of what the UniFi Video server knows
        about the camera
    :ivar list _isp_actionables: List of supported image settings
    :ivar int utc_h_offset: UTC offset in hours
    """

    def _load_data(self, data):

        self.model = data.get('model', None)

        if not self.model or not models.get(self.model, None):
            raise CameraModelError

        self._data = data
        self._id = data['_id']
        self.name = data.get('name', None)
        self.platform = data.get('platform', None)
        self.overlay_text = data.get('osdSettings', {}).get('tag', None)
        self.mac_addr = utils.format_mac_addr(data.get('mac', 'ffffffffffff'))
        self._isp_actionables = determine_img_actionables(self.platform,
            self.model)

        try:
            self.utc_h_offset = int(data.get('deviceSettings', {})\
                .get('timezone', '').split('GMT').pop())
        except (TypeError, ValueError):
            self.utc_h_offset = 0

    def _simple_isp_actionable(self, setting_name, value):
        isp = self._data['ispSettings']
        if value == None:
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

    def snapshot(self, filename=None):
        """Take and download snapshot.

        :param filename: Filename to save the snapshot to. Optional.
        :type filename: str or None
        """

        return self._api.get(endpoints['snapshot'](self._id),
            filename if filename else 'snapshot-{}-{}.jpg'.format(
                self._id, int(time.time())))

    def recording_between(self, start_time, end_time, filename=None):
        """Download a recording of the camera's footage from an arbitrary
        timespan, between ``start_time`` and ``end_time``.

        :param str start_time: Start time
        :param str end_time: End time
        :param filename: Filename to save the recording to (a ZIP file).
            Will use whatever the server provides if ``None``.
        :type filename: str or None

        Note: times should be in the format ``YYYY-MM-DD HH:MM:SS``.
        """

        start_time = utils.tz_shift(self.utc_h_offset * 3600,
            utils.iso_str_to_epoch(start_time)) * 1000

        end_time = utils.tz_shift(self.utc_h_offset * 3600,
            utils.iso_str_to_epoch(end_time)) * 1000

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

        if pre_padding_secs != None:
            rec_settings['prePaddingSecs'] = pre_padding_secs

        if post_padding_secs != None:
            rec_settings['postPaddingSecs'] = post_padding_secs

        verify = deepcopy(rec_settings)
        self.update(True)
        return verify == self._data['recordingSettings']

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
# to contrast, brightness, saturateion, etc. as.
for actionable in common_isp_actionables:
    add_actionable(actionable)
