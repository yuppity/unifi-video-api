from __future__ import print_function, unicode_literals

import time

from .single import UnifiVideoSingle
from . import utils

endpoints = {
    'save': lambda x: 'camera/{}'.format(x),
    'data': lambda x: 'camera/{}'.format(x),
    'snapshot': lambda x: 'snapshot/camera/{}'.format(x),
}

class UnifiVideoCamera(UnifiVideoSingle):

    def _load_data(self, data):
        if not data:
            return

        self._data = data
        self._id = data['_id']
        self.name = data.get('name', None)
        self.model = data.get('model', None)
        self.platform = data.get('platform', None)
        self.overlay_text = data.get('osdSettings', {}).get('tag', None)

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
