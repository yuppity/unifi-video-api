from __future__ import print_function, unicode_literals
from functools import wraps

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
    actionables = map(lambda x: x[0], common_isp_actionables)
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
                return None
            if not val:
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
        if not value:
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
        if not value:
            return isp.get(setting_name, -1)
        isp[setting_name] = value
        self.update(True)
        if isp[setting_name] == value:
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
        or an `int` between `0` and `3`.

        :param wdr: New WDR value
        :type wdr: int or None

        :return: If value provided: `True` or `False`, depending on
            whether new value was registered. If no value provided: current
            WDR value.

        :rtype: `bool` or `int`
        """

        if 'wdr' not in self._isp_actionables:
            raise NotImplementedError('This camera model ({}) has no ' \
                'support controlling WDR (dynamic range)'.format(
                    self.model))

        return self._simple_isp_actionable('wdr', wdr)

    def ir_leds(self, led_state):
        if 'irLedMode' not in self._isp_actionables:
            return None
        isp = self._data.get('ispSettings', {})
        isp['irLedLevel'] = 215
        if led_state == 'auto':
            isp['irLedMode'] = 'auto'
        elif led_state == 'on':
            isp['irLedMode'] = 'manual'
        elif led_state == 'off':
            isp['irLedMode'] = 'manual'
            isp['irLedLevel'] = 0
        else:
            return
        verify = isp['irLedMode'] + str(isp['irLedLevel'])
        self.update(True)
        if isp['irLedMode'] + str(isp['irLedLevel']) == verify:
            return True
        else:
            return False

    def set_onscreen_text(self, text):
        osd = self._data.get('osdSettings', {})
        osd['overrideMessage'] = True
        osd['tag'] = text.strip()
        self.update(True)

    def enable_onscreen_timestamp(self, on):
        osd = self._data.get('osdSettings', {})
        osd['enableDate'] = 1 if on else 0
        self.update(True)

    def enable_onscreen_watermark(self, on):
        osd = self._data.get('osdSettings', {})
        osd['enableLogo'] = 1 if on else 0
        self.update(True)

    def set_recording_settings(self, full_time_record_enabled=None,
            motion_record_enabled=None, pre_padding_secs=None,
            post_padding_secs=None):

        rec_settings = self._data.get('recordingSettings', {})

        for k, v in utils.get_arguments().items():
            if v is None:
                continue
            _k = utils.camel_to_snake(k)
            if 'padding' in k:
                rec_settings[_k] = int(v)
            else:
                rec_settings[_k] = bool(v)

        self.update(True)

    def __str__(self):
        _filter = ['name', 'model', 'platform']
        return '{}: {}'.format(
            type(self).__name__,
            {k: v for k, v in self.__dict__.items() if k in _filter})

for actionable in common_isp_actionables:
    add_actionable(actionable)
