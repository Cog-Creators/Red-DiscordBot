import six
import json
import ujson
from aioredis import Redis
from aioredis.commands import Pipeline


class Path(object):
    """
    This class represents a path in a JSON value
    """

    strPath = ""

    @staticmethod
    def rootPath():
        """Returns the root path's string representation"""
        return "."

    def __init__(self, path):
        """
        Make a new path based on the string representation in `path`
        """
        self.strPath = path


def str_path(p):
    """Returns the string representation of a path if it is of class Path"""
    if isinstance(p, Path):
        return p.strPath
    else:
        return p


class Client(Redis):
    async def jsondel(self, name, path=Path.rootPath()):
        """
        Deletes the JSON value stored at key ``name`` under ``path``
        """
        return await self.execute(b"JSON.DEL", name, str_path(path))

    async def jsonget(self, name, *args, path=None, no_escape=False, encoding="utf-8"):
        """
        Get the object stored as a JSON value at key ``name``
        ``args`` is zero or more paths, and defaults to root path
        ```no_escape`` is a boolean flag to add no_escape option to get non-ascii characters
        """
        pieces = [name]
        if no_escape:
            pieces.append("noescape")

        if not path:
            if len(args) == 0:
                pieces.append(Path.rootPath())
            else:
                string = "."
                string += ".".join([str_path(p) for p in args])
                pieces.append(string)
        else:
            pieces.append(path)


        # Handle case where key doesn't exist. The JSONDecoder would raise a
        # TypeError exception since it can't decode None
        try:
            return await self.execute(b"JSON.GET", *pieces, encoding=encoding)
        except TypeError:
            return None

    async def jsonmget(self, path, *args, encoding="utf-8"):
        """
        Gets the objects stored as a JSON values under ``path`` from
        keys ``args``
        """
        pieces = []
        pieces.extend(args)
        pieces.append(str_path(path))
        return await self.execute(b"JSON.MGET", *pieces, encoding=encoding)

    async def jsonset(self, name, path, obj, nx=False, xx=False):
        """
        Set the JSON value at key ``name`` under the ``path`` to ``obj``
        ``nx`` if set to True, set ``value`` only if it does not exist
        ``xx`` if set to True, set ``value`` only if it exists
        """
        pieces = [name, str_path(path), ujson.dumps(obj)]

        # Handle existential modifiers
        if nx and xx:
            raise Exception(
                "nx and xx are mutually exclusive: use one, the " "other or neither - but not both"
            )
        elif nx:
            pieces.append("NX")
        elif xx:
            pieces.append("XX")
        return await self.execute(b"JSON.SET", *pieces)

    async def jsontype(self, name, path=Path.rootPath()):
        """
        Gets the type of the JSON value under ``path`` from key ``name``
        """
        return await self.execute("JSON.TYPE", name, str_path(path))

    async def jsonnumincrby(self, name, path, number):
        """
        Increments the numeric (integer or floating point) JSON value under
        ``path`` at key ``name`` by the provided ``number``
        """
        return await self.execute(b"JSON.NUMINCRBY", name, str_path(path), ujson.dumps(number))

    async def jsonnummultby(self, name, path, number):
        """
        Multiplies the numeric (integer or floating point) JSON value under
        ``path`` at key ``name`` with the provided ``number``
        """
        return await self.execute(b"JSON.NUMMULTBY", name, str_path(path), ujson.dumps(number))

    async def jsonstrappend(self, name, string, path=Path.rootPath()):
        """
        Appends to the string JSON value under ``path`` at key ``name`` the
        provided ``string``
        """
        return await self.execute(b"JSON.STRAPPEND", name, str_path(path), ujson.dumps(string))

    async def jsonstrlen(self, name, path=Path.rootPath()):
        """
        Returns the length of the string JSON value under ``path`` at key
        ``name``
        """
        return await self.execute(b"JSON.STRLEN", name, str_path(path))

    async def jsonarrappend(self, name, path=Path.rootPath(), *args):
        """
        Appends the objects ``args`` to the array under the ``path` in key
        ``name``
        """
        pieces = [name, str_path(path)]
        for o in args:
            pieces.append(ujson.dumps(o))
        return await self.execute(b"JSON.ARRAPPEND", *pieces)

    async def jsonarrindex(self, name, path, scalar, start=0, stop=-1):
        """
        Returns the index of ``scalar`` in the JSON array under ``path`` at key
        ``name``. The search can be limited using the optional inclusive
        ``start`` and exclusive ``stop`` indices.
        """
        return await self.execute(
            b"JSON.ARRINDEX", name, str_path(path), ujson.dumps(scalar), start, stop
        )

    async def jsonarrinsert(self, name, path, index, *args):
        """
        Inserts the objects ``args`` to the array at index ``index`` under the
        ``path` in key ``name``
        """
        pieces = [name, str_path(path), index]
        for o in args:
            pieces.append(ujson.dumps(o))
        return await self.execute(b"JSON.ARRINSERT", *pieces)

    async def jsonarrlen(self, name, path=Path.rootPath()):
        """
        Returns the length of the array JSON value under ``path`` at key
        ``name``
        """
        return await self.execute(b"JSON.ARRLEN", name, str_path(path))

    async def jsonarrpop(self, name, path=Path.rootPath(), index=-1):
        """
        Pops the element at ``index`` in the array JSON value under ``path`` at
        key ``name``
        """
        return await self.execute(b"JSON.ARRPOP", name, str_path(path), index)

    async def jsonarrtrim(self, name, path, start, stop):
        """
        Trim the array JSON value under ``path`` at key ``name`` to the
        inclusive range given by ``start`` and ``stop``
        """
        return await self.execute(b"JSON.ARRTRIM", name, str_path(path), start, stop)

    async def jsonobjkeys(self, name, path=Path.rootPath()):
        """
        Returns the key names in the dictionary JSON value under ``path`` at key
        ``name``
        """
        return await self.execute(b"JSON.OBJKEYS", name, str_path(path), encoding="utf-8")

    async def jsonobjlen(self, name, path=Path.rootPath()):
        """
        Returns the length of the dictionary JSON value under ``path`` at key
        ``name``
        """
        return await self.execute(b"JSON.OBJLEN", name, str_path(path))

    def pipeline(self):
        p = Pipeline(self._pool_or_conn)
        return p


class Pipeline(Pipeline, Client):
    """Pipeline for ReJSONClient"""
