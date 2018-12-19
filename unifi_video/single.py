class UnifiVideoSingle(object):
    """Base class that encapsulates common features of objects
    that have unique IDs and that UniFi Video stores in their own
    collection.

    Examples of possible "singles" and their corresponding MongoDB collections:

    - Cameras (``av.camera``)
    - Recordings (``av.event``)
    - Alerts (``av.alert``)
    - Firmwares (``av.firmware``)
    - Users (``av.user``)
    - Maps (``av.map``)

    :ivar _api: API instance
    :vartype _api: :class:`~unifi_video.api.UnifiVideoAPI`
    :ivar str _id: ID this single is identified as on the server side
    """

    def __init__(self, api, data=None):
        self._api = api
        self._id = None
        if data is not None:
            self._load_data(self._extract_data(data))

    def _load_data(self, data):
        raise NotImplementedError('Method is not implement in base class')

    def _extract_data(self, data):
        if not isinstance(data, dict) or \
                ('_id' not in data and 'data' not in data):

            raise ValueError('Instantiaton data to {} does not meet ' \
                'expectations. You might be using an unsupported version ' \
                'of Unifi NVR'.format(type(self).__name__))

        data = data['data'] if '_id' not in data and 'data' in data else data

        if isinstance(data, list):
            if not self._id:
                raise ValueError('{} has to be instantiated with a single ' \
                    'dict, not a list'.format(type(self).__name__))
            try:
                data = [i for i in data if i['_id'] == self._id][0]
            except (KeyError, IndexError):
                data = None

        return data
