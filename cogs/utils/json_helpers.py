import os
import discord
from collections import defaultdict
from cogs.utils.dataIO import dataIO

GLOBAL_KEY = '__global__'


class DataDB:
    """
    A helper class to streamline the saving of json files
    """
    def __init__(self, file_path, *, create_dirs=False, default_value=None):
        self.path = file_path

        path_exists = os.path.isfile(file_path)

        if create_dirs and not path_exists:
            path, _ = os.path.split(file_path)
            if path:
                try:
                    os.makedirs(path)
                except FileExistsError:
                    pass

        if path_exists:
            self._data = dataIO.load_json(file_path)
        else:
            self._data = {}
            self._save()

        if default_value is not None:
            def _get_default():
                return default_value
            self._data = defaultdict(_get_default, self._data)

    def set(self, key, value):
        """Sets a DB's entry"""
        self._data[key] = value
        self._save()

    def get(self, key, default=None):
        """Returns a DB's entry"""
        return self._data.get(key, default)

    def remove(self, key):
        """Removes a DB's entry"""
        del self._data[key]
        self._save()

    def wipe(self):
        """Wipes DB"""
        self._data = {}
        self._save()

    def all(self):
        """Returns all DB's data"""
        return self._data

    def _save(self):
        dataIO.save_json(self.path, self._data)

    def __contains__(self, key):
        return key in self._data

    def __getitem__(self, key):
        return self._data[key]

    def __len__(self):
        return len(self._data)


class ServerDB(DataDB):
    """
    A helper class to streamline the saving of server based json data
    """

    def __init__(self, *args, global_defaults={}, **kwargs):
        super().__init__(*args, **kwargs)
        self._global_defaults = global_defaults

    def set(self, server, key, value):
        """Sets a server's entry"""
        if not isinstance(server, discord.Server):
            raise TypeError('Can only set server data')
        if server.id not in self._data:
            self._data[server.id] = {}
        self._data[server.id][key] = value
        self._save()

    def get(self, server, key):
        """Returns a server's entry"""
        if not isinstance(server, discord.Server):
            raise TypeError('Can only get server data')
        return self._data[server.id][key]

    def remove(self, server, key):
        """Removes a server's entry"""
        if not isinstance(server, discord.Server):
            raise TypeError('Can only remove server data')
        del self._data[server.id][key]
        self._save()

    def get_all(self, server):
        """Returns all entries of a server"""
        if not isinstance(server, discord.Server):
            raise TypeError('Can only get server data')
        return self._data[server.id]

    def remove_all(self, server):
        """Removes all entries of a server"""
        if not isinstance(server, discord.Server):
            raise TypeError('Can only remove servers')
        super().remove(server.id)
        self._save()

    def set_global(self, key, value):
        """Sets a global value"""
        if GLOBAL_KEY not in self._data:
            self._data[GLOBAL_KEY] = {}
        self._data[GLOBAL_KEY][key] = value
        self._save()

    def get_global(self, key):
        """Gets a global value"""
        if GLOBAL_KEY not in self._data:
            return self._global_defaults[key]

        if key in self._data[GLOBAL_KEY]:
            return self._data[GLOBAL_KEY][key]
        return self._global_defaults[key]
