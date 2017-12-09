from __future__ import absolute_import

import sys
from collections import abc
from collections.abc import Iterable, Set

from cpython.object cimport PyObject_Str

from ._abc import MultiMapping, MutableMultiMapping
from ._istr import istr

cdef object _marker = object()

upstr = istr  # for relaxing backward compatibility problems
cdef object _istr = istr


def getversion(_Base md):
    return md._impl._version


cdef _eq(self, other):
    cdef int is_left_base, is_right_base
    cdef Py_ssize_t i, l
    cdef list lft_items, rgt_items
    cdef _Pair lft, rgt

    is_left_base = isinstance(self, _Base)
    is_right_base = isinstance(other, _Base)

    if is_left_base and is_right_base:
        lft_items = (<_Base>self)._impl._items
        rgt_items = (<_Base>other)._impl._items
        l = len(lft_items)
        if l != len(rgt_items):
            return False
        for i in range(l):
            lft = <_Pair>(lft_items[i])
            rgt = <_Pair>(rgt_items[i])
            if lft._hash != rgt._hash:
                return False
            if lft._identity != rgt._identity:
                return False
            if lft._value != rgt._value:
                return False
        return True
    elif is_left_base and isinstance(other, abc.Mapping):
        return (<_Base>self)._eq_to_mapping(other)
    elif is_right_base and isinstance(self, abc.Mapping):
        return (<_Base>other)._eq_to_mapping(self)
    else:
        return NotImplemented


cdef class _Pair:
    cdef str _identity
    cdef Py_hash_t _hash
    cdef str _key
    cdef object _value

    def __cinit__(self, identity, key, value):
        self._hash = hash(identity)
        self._identity = <str>identity
        self._key = <str>key
        self._value = value


cdef unsigned long long _version


cdef class _Impl:
    cdef list _items
    cdef unsigned long long _version

    def __cinit__(self):
        self._items = []
        self.incr_version()

    cdef void incr_version(self):
        global _version
        _version += 1
        self._version = _version


cdef class _Base:

    cdef _Impl _impl

    cdef str _title(self, s):
        typ = type(s)
        if typ is str:
            return <str>s
        elif typ is _istr:
            return PyObject_Str(s)
        else:
            return str(s)

    def getall(self, key, default=_marker):
        """Return a list of all values matching the key."""
        return self._getall(self._title(key), key, default)

    cdef _getall(self, str identity, key, default):
        cdef list res
        cdef _Pair item
        cdef Py_hash_t h = hash(identity)
        res = []
        for i in self._impl._items:
            item = <_Pair>i
            if item._hash != h:
                continue
            if item._identity == identity:
                res.append(item._value)
        if res:
            return res
        elif default is not _marker:
            return default
        else:
            raise KeyError('Key not found: %r' % key)

    def getone(self, key, default=_marker):
        """Get first value matching the key."""
        return self._getone(self._title(key), key, default)

    cdef _getone(self, str identity, key, default):
        cdef _Pair item
        cdef Py_hash_t h = hash(identity)
        for i in self._impl._items:
            item = <_Pair>i
            if item._hash != h:
                continue
            if item._identity == identity:
                return item._value
        if default is not _marker:
            return default
        raise KeyError('Key not found: %r' % key)

    # Mapping interface #

    def __getitem__(self, key):
        return self._getone(self._title(key), key, _marker)

    def get(self, key, default=None):
        """Get first value matching the key.

        The method is alias for .getone().
        """
        return self._getone(self._title(key), key, default)

    def __contains__(self, key):
        return self._contains(self._title(key))

    cdef _contains(self, str identity):
        cdef _Pair item
        cdef Py_hash_t h = hash(identity)
        for i in self._impl._items:
            item = <_Pair>i
            if item._hash != h:
                continue
            if item._identity == identity:
                return True
        return False

    def __iter__(self):
        return iter(self.keys())

    def __len__(self):
        return len(self._impl._items)

    cpdef keys(self):
        """Return a new view of the dictionary's keys."""
        return _KeysView.__new__(_KeysView, self._impl)

    def items(self):
        """Return a new view of the dictionary's items *(key, value) pairs)."""
        return _ItemsView.__new__(_ItemsView, self._impl)

    def values(self):
        """Return a new view of the dictionary's values."""
        return _ValuesView.__new__(_ValuesView, self._impl)

    def __repr__(self):
        cdef _Pair item
        lst = []
        for i in self._impl._items:
            item = <_Pair>i
            lst.append("'{}': {!r}".format(item._key, item._value))
        body = ', '.join(lst)
        return '<{}({})>'.format(self.__class__.__name__, body)

    cdef _eq_to_mapping(self, other):
        cdef _Pair item
        if len(self._impl._items) != len(other):
            return False
        for i in self._impl._items:
            item = <_Pair>i
            for k, v in other.items():
                if self._title(k) != item._identity:
                    continue
                if v == item._value:
                    break
            else:
                return False
        return True

    def __richcmp__(self, other, op):
        if op == 2:  # ==
            return _eq(self, other)
        elif op == 3:  # !=
            ret = _eq(self, other)
            if ret is NotImplemented:
                return ret
            else:
                return not ret
        else:
            return NotImplemented


cdef class MultiDictProxy(_Base):
    _proxy_classes = (MultiDict, MultiDictProxy)
    _base_class = MultiDict

    def __init__(self, arg):
        cdef _Base base
        if not isinstance(arg, self._proxy_classes):
            raise TypeError(
                'ctor requires {} instance'
                ', not {}'.format(
                    ' or '.join(self._proxy_classes),
                    type(arg)))

        base = arg
        self._impl = base._impl

    def __reduce__(self):
        raise TypeError("can't pickle {} objects"
                        .format(self.__class__.__name__))

    def copy(self):
        """Return a copy of itself."""
        return self._base_class(self)

MultiMapping.register(MultiDictProxy)


cdef class CIMultiDictProxy(MultiDictProxy):
    _proxy_classes = (CIMultiDict, CIMultiDictProxy)
    _base_class = CIMultiDict

    cdef str _title(self, s):
        typ = type(s)
        if typ is str:
            return <str>(s.title())
        elif type(s) is _istr:
            return PyObject_Str(s)
        return s.title()


MultiMapping.register(CIMultiDictProxy)


cdef str _str(key):
    typ = type(key)
    if typ is str:
        return <str>key
    if typ is _istr:
        return PyObject_Str(key)
    elif issubclass(typ, str):
        return str(key)
    else:
        raise TypeError("MultiDict keys should be either str "
                        "or subclasses of str")


cdef class MultiDict(_Base):
    """An ordered dictionary that can have multiple values for each key."""

    def __init__(self, *args, **kwargs):
        self._impl = _Impl()
        self._extend(args, kwargs, 'MultiDict', True)

    def __reduce__(self):
        return (
            self.__class__,
            (list(self.items()),)
        )

    cdef _extend(self, tuple args, dict kwargs, name, bint do_add):
        cdef _Pair item
        cdef object key

        if len(args) > 1:
            raise TypeError("{} takes at most 1 positional argument"
                            " ({} given)".format(name, len(args)))

        if args:
            arg = args[0]
            if isinstance(arg, _Base):
                for i in (<_Base>arg)._impl._items:
                    item = <_Pair>i
                    key = item._key
                    value = item._value
                    if do_add:
                        self._add(key, value)
                    else:
                        self._replace(key, value)
            elif hasattr(arg, 'items'):
                for i in arg.items():
                    if isinstance(i, _Pair):
                        item = <_Pair>i
                        key = item._key
                        value = item._value
                    else:
                        key = i[0]
                        value = i[1]
                    if do_add:
                        self._add(key, value)
                    else:
                        self._replace(key, value)
            else:
                for i in arg:
                    if isinstance(i, _Pair):
                        item = <_Pair>i
                        key = item._key
                        value = item._value
                    else:
                        if not len(i) == 2:
                            raise TypeError(
                                "{} takes either dict or list of (key, value) "
                                "tuples".format(name))
                        key = i[0]
                        value = i[1]
                    if do_add:
                        self._add(key, value)
                    else:
                        self._replace(key, value)


        for key, value in kwargs.items():
            if do_add:
                self._add(key, value)
            else:
                self._replace(key, value)

    cdef _add(self, key, value):
        self._impl._items.append(_Pair.__new__(
            _Pair, self._title(key), _str(key), value))
        self._impl.incr_version()

    cdef _replace(self, key, value):
        cdef str identity = self._title(key)
        cdef str k = _str(key)
        cdef Py_hash_t h = hash(identity)
        cdef Py_ssize_t i, rgt
        cdef _Pair item
        cdef list items = self._impl._items

        for i in range(len(items)-1, -1, -1):
            item = <_Pair>items[i]
            if h != item._hash:
                continue
            if item._identity == identity:
                item._key = k
                item._value = value
                # i points to last found item
                rgt = i
                self._impl.incr_version()
                break
        else:
            self._impl._items.append(_Pair.__new__(_Pair, identity, k, value))
            self._impl.incr_version()
            return

        # remove all precending items
        i = 0
        while i < rgt:
            item = <_Pair>items[i]
            if h == item._hash and item._identity == identity:
                del items[i]
                rgt -= 1
            else:
                i += 1

    def add(self, key, value):
        """Add the key and value, not overwriting any previous value."""
        self._add(key, value)

    def copy(self):
        """Return a copy of itself."""
        ret = MultiDict()
        ret._extend((list(self.items()),), {}, 'copy', True)
        return ret

    def extend(self, *args, **kwargs):
        """Extend current MultiDict with more values.

        This method must be used instead of update.
        """
        self._extend(args, kwargs, "extend", True)

    def clear(self):
        """Remove all items from MultiDict"""
        self._impl._items.clear()
        self._impl.incr_version()

    # MutableMapping interface #

    def __setitem__(self, key, value):
        self._replace(key, value)

    def __delitem__(self, key):
        self._remove(key)

    cdef _remove(self, key):
        cdef _Pair item
        cdef bint found = False
        cdef str identity = self._title(key)
        cdef Py_hash_t h = hash(identity)
        cdef list items = self._impl._items
        for i in range(len(items) - 1, -1, -1):
            item = <_Pair>items[i]
            if item._hash != h:
                continue
            if item._identity == identity:
                del items[i]
                found = True
        if not found:
            raise KeyError(key)
        else:
            self._impl.incr_version()

    def setdefault(self, key, default=None):
        """Return value for key, set value to default if key is not present."""
        cdef _Pair item
        cdef str identity = self._title(key)
        cdef Py_hash_t h = hash(identity)
        cdef list items = self._impl._items
        for i in items:
            item = <_Pair>i
            if item._hash != h:
                continue
            if item._identity == identity:
                return item._value
        self._add(key, default)
        return default

    def popone(self, key, default=_marker):
        """Remove the last occurrence of key and return the corresponding
        value.

        If key is not found, default is returned if given, otherwise
        KeyError is raised.

        """
        cdef object value = None
        cdef str identity = self._title(key)
        cdef Py_hash_t h = hash(identity)
        cdef _Pair item
        cdef list items = self._impl._items
        for i in range(len(items)):
            item = <_Pair>items[i]
            if item._hash != h:
                continue
            if item._identity == identity:
                value = item._value
                del items[i]
                self._impl.incr_version()
                return value
        if default is _marker:
            raise KeyError(key)
        else:
            return default

    pop = popone

    def popall(self, key, default=_marker):
        """Remove all occurrences of key and return the list of corresponding
        values.

        If key is not found, default is returned if given, otherwise
        KeyError is raised.

        """
        cdef bint found = False
        cdef str identity = self._title(key)
        cdef Py_hash_t h = hash(identity)
        cdef _Pair item
        cdef list items = self._impl._items
        cdef list ret = []
        for i in range(len(items)-1, -1, -1):
            item = <_Pair>items[i]
            if item._hash != h:
                continue
            if item._identity == identity:
                ret.append(item._value)
                del items[i]
                self._impl.incr_version()
                found = True
        if not found:
            if default is _marker:
                raise KeyError(key)
            else:
                return default
        else:
            ret.reverse()
            return ret

    def popitem(self):
        """Remove and return an arbitrary (key, value) pair."""
        cdef _Pair item
        cdef list items = self._impl._items
        if items:
            item = <_Pair>items.pop(0)
            self._impl.incr_version()
            return (item._key, item._value)
        else:
            raise KeyError("empty multidict")

    def update(self, *args, **kwargs):
        """Update the dictionary from *other*, overwriting existing keys."""
        self._extend(args, kwargs, "update", False)


MutableMultiMapping.register(MultiDict)


cdef class CIMultiDict(MultiDict):
    """An ordered dictionary that can have multiple values for each key."""

    def __init__(self, *args, **kwargs):
        self._impl = _Impl()
        self._extend(args, kwargs, 'CIMultiDict', True)

    def __reduce__(self):
        return (
            self.__class__,
            (list(self.items()),),
        )

    cdef str _title(self, s):
        typ = type(s)
        if typ is str:
            return <str>(s.title())
        elif type(s) is _istr:
            return PyObject_Str(s)
        return s.title()

    def copy(self):
        """Return a copy of itself."""
        ret = CIMultiDict()
        ret._extend((list(self.items()),), {}, 'copy', True)
        return ret



MutableMultiMapping.register(CIMultiDict)


cdef class _ViewBase:

    cdef _Impl _impl

    def __cinit__(self, _Impl impl):
        self._impl = impl

    def __len__(self):
        return len(self._impl._items)


cdef class _ViewBaseSet(_ViewBase):

    def __richcmp__(self, other, op):
        if op == 0:  # <
            if not isinstance(other, Set):
                return NotImplemented
            return len(self) < len(other) and self <= other
        elif op == 1:  # <=
            if not isinstance(other, Set):
                return NotImplemented
            if len(self) > len(other):
                return False
            for elem in self:
                if elem not in other:
                    return False
            return True
        elif op == 2:  # ==
            if not isinstance(other, Set):
                return NotImplemented
            return len(self) == len(other) and self <= other
        elif op == 3:  # !=
            return not self == other
        elif op == 4:  #  >
            if not isinstance(other, Set):
                return NotImplemented
            return len(self) > len(other) and self >= other
        elif op == 5:  # >=
            if not isinstance(other, Set):
                return NotImplemented
            if len(self) < len(other):
                return False
            for elem in other:
                if elem not in self:
                    return False
            return True

    def __and__(self, other):
        if not isinstance(other, Iterable):
            return NotImplemented
        if isinstance(self, _ViewBaseSet):
            self = set(iter(self))
        if isinstance(other, _ViewBaseSet):
            other = set(iter(other))
        if not isinstance(other, Set):
            other = set(iter(other))
        return self & other

    def __or__(self, other):
        if not isinstance(other, Iterable):
            return NotImplemented
        if isinstance(self, _ViewBaseSet):
            self = set(iter(self))
        if isinstance(other, _ViewBaseSet):
            other = set(iter(other))
        if not isinstance(other, Set):
            other = set(iter(other))
        return self | other

    def __sub__(self, other):
        if not isinstance(other, Iterable):
            return NotImplemented
        if isinstance(self, _ViewBaseSet):
            self = set(iter(self))
        if isinstance(other, _ViewBaseSet):
            other = set(iter(other))
        if not isinstance(other, Set):
            other = set(iter(other))
        return self - other

    def __xor__(self, other):
        if not isinstance(other, Iterable):
            return NotImplemented
        if isinstance(self, _ViewBaseSet):
            self = set(iter(self))
        if isinstance(other, _ViewBaseSet):
            other = set(iter(other))
        if not isinstance(other, Set):
            other = set(iter(other))
        return self ^ other


cdef class _ItemsIter:
    cdef _Impl _impl
    cdef int _current
    cdef int _len
    cdef unsigned long long _version

    def __cinit__(self, _Impl impl):
        self._impl = impl
        self._current = 0
        self._version = impl._version
        self._len = len(impl._items)

    def __iter__(self):
        return self

    def __next__(self):
        if self._version != self._impl._version:
            raise RuntimeError("Dictionary changed during iteration")
        if self._current == self._len:
            raise StopIteration
        item = <_Pair>self._impl._items[self._current]
        self._current += 1
        return (item._key, item._value)


cdef class _ItemsView(_ViewBaseSet):

    def isdisjoint(self, other):
        'Return True if two sets have a null intersection.'
        cdef _Pair item
        for i in self._impl._items:
            item = <_Pair>i
            t = (item._key, item._value)
            if t in other:
                return False
        return True

    def __contains__(self, i):
        cdef _Pair item
        cdef str key
        cdef object value
        assert isinstance(i, tuple) or isinstance(i, list)
        assert len(i) == 2
        key = i[0]
        value = i[1]
        for item in self._impl._items:
            if key == item._key and value == item._value:
                return True
        return False

    def __iter__(self):
        return _ItemsIter.__new__(_ItemsIter, self._impl)

    def __repr__(self):
        cdef _Pair item
        lst = []
        for i in self._impl._items:
            item = <_Pair>i
            lst.append("{!r}: {!r}".format(item._key, item._value))
        body = ', '.join(lst)
        return '{}({})'.format(self.__class__.__name__, body)


abc.ItemsView.register(_ItemsView)


cdef class _ValuesIter:
    cdef _Impl _impl
    cdef int _current
    cdef int _len
    cdef unsigned long long _version

    def __cinit__(self, _Impl impl):
        self._impl = impl
        self._current = 0
        self._len = len(impl._items)
        self._version = impl._version

    def __iter__(self):
        return self

    def __next__(self):
        if self._version != self._impl._version:
            raise RuntimeError("Dictionary changed during iteration")
        if self._current == self._len:
            raise StopIteration
        item = <_Pair>self._impl._items[self._current]
        self._current += 1
        return item._value


cdef class _ValuesView(_ViewBase):

    def __contains__(self, value):
        cdef _Pair item
        for i in self._impl._items:
            item = <_Pair>i
            if item._value == value:
                return True
        return False

    def __iter__(self):
        return _ValuesIter.__new__(_ValuesIter, self._impl)

    def __repr__(self):
        cdef _Pair item
        lst = []
        for i in self._impl._items:
            item = <_Pair>i
            lst.append("{!r}".format(item._value))
        body = ', '.join(lst)
        return '{}({})'.format(self.__class__.__name__, body)


abc.ValuesView.register(_ValuesView)


cdef class _KeysIter:
    cdef _Impl _impl
    cdef int _current
    cdef int _len
    cdef unsigned long long _version

    def __cinit__(self, _Impl impl):
        self._impl = impl
        self._current = 0
        self._len = len(self._impl._items)
        self._version = impl._version

    def __iter__(self):
        return self

    def __next__(self):
        if self._version != self._impl._version:
            raise RuntimeError("Dictionary changed during iteration")
        if self._current == self._len:
            raise StopIteration
        item = <_Pair>self._impl._items[self._current]
        self._current += 1
        return item._key


cdef class _KeysView(_ViewBaseSet):

    def isdisjoint(self, other):
        'Return True if two sets have a null intersection.'
        cdef _Pair item
        for i in self._impl._items:
            item = <_Pair>i
            if item._key in other:
                return False
        return True

    def __contains__(self, value):
        cdef _Pair item
        for i in self._impl._items:
            item = <_Pair>i
            if item._key == value:
                return True
        return False

    def __iter__(self):
        return _KeysIter.__new__(_KeysIter, self._impl)

    def __repr__(self):
        cdef _Pair item
        lst = []
        for i in self._impl._items:
            item = <_Pair>i
            lst.append("{!r}".format(item._key))
        body = ', '.join(lst)
        return '{}({})'.format(self.__class__.__name__, body)


abc.KeysView.register(_KeysView)
