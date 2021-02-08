from __future__ import print_function, unicode_literals

from .single import UnifiVideoSingle
from datetime import datetime

endpoints = {
    'recording': lambda x: 'recording/{}'.format(x),
    'download': lambda x: 'recording/{}/download'.format(x),
    'delete': lambda x: 'recording?recordings[]={}&confirmed=true'.format(x),
    'snapshot': lambda c, d, r, w: \
        'snapshot/recording/{}/{}/{}{}'.format(c,
            d.strftime('%Y/%m/%d'), r, '?width={}'.format(w) if w else ''),
    'motion': lambda x: 'recording/{}/motion?alpha=true'.format(x),
}

class UnifiVideoRecording(UnifiVideoSingle):
    """Recording container

    Attributes:
        _id (str): Recording ID (MongoDB ObjectID as hex string)
        start_time (datetime): Recording start time and date (local time)
        end_time (datetime): Recording end time and date (local time)
        start_time_utc (datetime): Recording start time and date (UTC)
        end_time_utc (datetime): Recording end time and date (UTC)
        rec_type (str): Recording type. Either `motionRecording`,
            or `fullTimeRecording`.
        locked (bool, NoneType): Whether or not recording is locked
        in_progress (bool, NoneType): Recording is in progress
        marked_for_deletion (bool, NoneType): Recording is marked for deletion
        cameras (list): List of camera IDs
    """

    def _load_data(self, data):
        if not data:
            return

        self._data = data
        self._id = data['_id']
        self.rec_type = data.get('eventType', None)
        self.locked = data.get('locked', None)
        self.in_progress = data.get('inProgress', None)
        self.marked_for_deletion = data.get('markedForDeletion', None)
        self.cameras = data.get('cameras', [])
        self.start_time = datetime.fromtimestamp(
            int(data.get('startTime', 0) / 1000))
        self.end_time = datetime.fromtimestamp(
            int(data.get('endTime', 0) / 1000))
        self.start_time_utc = datetime.utcfromtimestamp(
            int(data.get('startTime', 0) / 1000))
        self.end_time_utc = datetime.utcfromtimestamp(
            int(data.get('endTime', 0) / 1000))

    def download(self, filename=None):
        """Download recording

        Arguments:
            filename (str, NoneType, bool): Filename (`str`) to save the
                image as or ``True`` (`bool`) if you want the response body
                as a return value. You can also leave this out or set it to
                ``None`` or ``False`` and a filename will be generated for you.

        Return value:
            Depends on input params.

            - When ``filename`` is `str`, `NoneType` or ``False``: `True` if
              write to file was successful, otherwise `NoneType`

            - When ``filename`` is ``True``: raw response body (`str`)
        """

        return self._api.get(endpoints['download'](self._id),
            filename if filename else 'recording-{}-{}.mp4'.format(
                self._id, self.start_time.isoformat()))

    def motion(self, filename=None):
        """Download recording motion

        Arguments:
            filename (str, NoneType, bool): Filename (`str`) to save the
                image as or ``True`` (`bool`) if you want the response body
                as a return value. You can also leave this out or set it to
                ``None`` or ``False`` and a filename will be generated for you.

        Return value:
            Depends on input params.

            - When ``filename`` is `str`, `NoneType` or ``False``: `True` if
              write to file was successful, otherwise `NoneType`

            - When ``filename`` is ``True``: raw response body (`str`)
        """

        if self.rec_type == 'fullTimeRecording':
            return False

        return self._api.get(endpoints['motion'](self._id),
            filename if filename else 'motion-{}.png'.format(self._id))

    def snapshot(self, width=0, filename=None):
        """Download recording thumbnail

        Arguments:
            width (int): Image pixel width. If 0 (of False), return maximum size
            filename (str, NoneType, bool): Filename (`str`) to save the
                image as or ``True`` (`bool`) if you want the response body
                as a return value. You can also leave this out or set it to
                ``None`` or ``False`` and a filename will be generated for you.

        Return value:
            Depends on input params.

            - When ``filename`` is `str`, `NoneType` or ``False``: `True` if
              write to file was successful, otherwise `NoneType`

            - When ``filename`` is ``True``: raw response body (`str`)
        """

        return self._api.get(endpoints['snapshot'](self.cameras[0],
            self.start_time, self._id, int(width)), filename if filename else \
                    'recording-{}-{}.jpg'.format(self._id,
                        self.start_time.isoformat()))

    def delete(self):
        """Delete recording
        """
        return self._api.delete(endpoints['delete'](self._id))

    def refresh(self):
        '''Refresh recording's data from UniFi Video
        '''
        self._load_data(
            self._extract_data(
                self._api.get(endpoints['recording'](self._id))))

    def _control_lock(self, remove=False, verify=False):
        '''Control recording's lock state

        Arguments:
            remove (bool):
                Remove lock
            verify (bool):
                Refetch recording data from UniFi Video to verify
                the action was registered

        Returns:
            bool: Action success
        '''

        if self.locked is not remove:
            return True

        new_rec_state = dict(self._data)
        new_rec_state['locked'] = not remove

        put_success = self._api.put(
            endpoints['recording'](self._id), data=new_rec_state)

        if not put_success:
            return False

        if verify:
            self.refresh()
        else:
            self._load_data(self._extract_data(put_success))

        return self.locked is not remove

    def lock(self, verify=False):
        '''Lock recording

        Arguments:
            verify (bool):
                Refetch recording data from UniFi Video to verify
                the lock was registered

        Returns:
            bool: Action success
        '''
        return self._control_lock(remove=False, verify=verify)

    def unlock(self, verify=False):
        '''Unlock recording

        Arguments:
            verify (bool):
                Refetch recording data from UniFi Video to verify
                the lock was registered

        Returns:
            bool: Action success
        '''
        return self._control_lock(remove=True, verify=verify)

    def __str__(self):
        return '{}: {}'.format(type(self).__name__, {
            '_id': self._id,
            'rec_type': self.rec_type,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat()
        })
