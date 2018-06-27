import collections


class LRUDict(collections.OrderedDict):
    """
    dict with LRU-eviction and max-size for caching

    This may not behave as intended if not used for caching
    Values cannot be updated in place. 
    pop them, and replace them if needed.
    """

    # Note on usage of super in below methods:
    # because of the interactions of some methods,
    # using super is needed to avoid some issues
    # This could have been done more neatly by doing a full implementation
    # But this is about as efficient as it gets with the minimal amount of code
    # needed to do it

    def __init__(self, *keyval_pairs, size):
        self.size = size
        super(LRUDict, self).__init__(*keyval_pairs)

    def __contains__(self, key):
        if super().__contains__(key):
            self.move_to_end(key, last=True)
            return True
        return False

    def __getitem__(self, key):
        # This will end up calling our overwritten contains.
        try:
            ret = super().__getitem__(key)
        except KeyError:
            raise
        else:
            return ret

    def __setitem__(self, key, value):
        if not super().__contains__(key):
            super().__setitem__(key, value)
            if len(self) > self.size:
                try:
                    self.popitem(last=False)
                except:
                    pass
        else:
            raise KeyError("This does not allow rewriting existing values")
