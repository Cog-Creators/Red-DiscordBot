import collections


class LRUDict(collections.OrderedDict):
    """
    dict with LRU-eviction and max-size for caching

    This may not behave as intended if not used for caching
    Don't update values in place.
    """

    def __init__(self, size):
        self.size = size
        super(LRUDict, self).__init__()

    def __contains__(self, key):
        if super().__contains__(key):
            self.move_to_end(key, last=False)
            return True
        return False

    def __getitem__(self, key):
        try:
            ret = self.pop(key)
        except KeyError:
            raise
        else:
            self[key] = ret
            return ret

    def __setitem__(self, key, value):
        if not super().__contains__(key):  # PITA avoidance of overriden contains
            super().__setitem__(key, value)
            if len(self) > self.size:
                try:
                    self.popitem(last=False)
                except:
                    pass
        else:
            raise KeyError("This does not allow rewriting existing values")
