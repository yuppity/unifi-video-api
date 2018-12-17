from __future__ import print_function, unicode_literals

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
        'features': [
            'optical_zoom'
        ]
    },

    'UVC G3 Pro': {
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

class CameraModelError(ValueError):
    def __init__(self, *args, **kwargs):
        super(CameraModelError, self).__init__(self, *args, **kwargs)

class UnifiVideoCamera(UnifiVideoSingle):

    def _load_data(self, data):

        self.model = data.get('model', None)

        if not self.model or not models.get(self.model, None):
            raise CameraModelError('Unsupported camera model')

        self._data = data
        self._id = data['_id']
        self.name = data.get('name', None)
        self.platform = data.get('platform', None)
        self.overlay_text = data.get('osdSettings', {}).get('tag', None)
        self.mac_addr = utils.format_mac_addr(data.get('mac', 'ffffffffffff'))

        try:
            self.utc_h_offset = int(data.get('deviceSettings', {})\
                .get('timezone', '').split('GMT').pop())
        except (TypeError, ValueError):
            self.utc_h_offset = 0

    def update(self, save=False):
        if save:
            self._load_data(self._extract_data(
                self._api.put(endpoints['save'](self._id), self._data)))
        else:
            self._load_data(self._extract_data(
                self._api.get(endpoints['data'](self._id))))

    def snapshot(self, filename=None):
        return self._api.get(endpoints['snapshot'](self._id),
            filename if filename else 'snapshot-{}-{}.jpg'.format(
                self._id, int(time.time())))

    def recording_between(self, start_time, end_time, filename=None):
        start_time = utils.tz_shift(self.utc_h_offset * 3600,
            utils.iso_str_to_epoch(start_time)) * 1000

        end_time = utils.tz_shift(self.utc_h_offset * 3600,
            utils.iso_str_to_epoch(end_time)) * 1000

        return self._api.get(endpoints['recording_span'](
            self._id, start_time, end_time), filename if filename else '')

    def ir_leds(self, on):
        isp = self._data.get('ispSettings', {})

        if on is 'auto':
            isp['irLedMode'] = 'auto'
        elif on:
            isp['irLedMode'] = 'manual'

            # UniFi Video sets this to 215 when using the UVC G3.
            # It seems unlikely this is a universal "on" value
            # that would work for all Ubiquiti cameras.
            isp['irLedLevel'] = 215
        else:
            isp['irLedMode'] = 'manual'
            isp['irLedLevel'] = 0

        self.update(True)

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
