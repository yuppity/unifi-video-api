try:
    from six import itervalues
except (ImportError, ModuleNotFoundError):
    from ._six import itervalues

class UnifiVideoCollection(dict):
    def __init__(self, collection_type, *args, **kwargs):
        self._collection_type = collection_type
        self.update(*args, **kwargs)

    def __iter__(self, *args, **kwargs):
        return itervalues(self, **kwargs)

    def add(self, single_dict):
        if not isinstance(single_dict, self._collection_type):
            raise ValueError('Cannot add items other than of type {}'.format(
                self._collection_type.__name__))
        self[single_dict._id] = single_dict

    def __contains__(self, item):
        if isinstance(item, self._collection_type) and hasattr(item, '_id'):
            item = item._id
        return super(UnifiVideoCollection, self).__contains__(item)
