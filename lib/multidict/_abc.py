import abc

from collections.abc import Mapping, MutableMapping


class MultiMapping(Mapping):

    @abc.abstractmethod
    def getall(self, key, default=None):
        raise KeyError

    @abc.abstractmethod
    def getone(self, key, default=None):
        raise KeyError


class MutableMultiMapping(MultiMapping, MutableMapping):

    @abc.abstractmethod
    def add(self, key, value):
        raise NotImplementedError

    @abc.abstractmethod
    def extend(self, *args, **kwargs):
        raise NotImplementedError

    @abc.abstractmethod
    def popone(self, key, default=None):
        raise KeyError

    @abc.abstractmethod
    def popall(self, key, default=None):
        raise KeyError
