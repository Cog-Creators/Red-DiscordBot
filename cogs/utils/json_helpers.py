import os
from cogs.utils.dataIO import dataIO

class DataDB:
    """
    A helper class to streamline the saving of json files
    """
    def __init__(self, file_path, *, create_dirs=False):
        self.path = file_path

        if create_dirs:
            self._create_dirs(file_path)

        if os.path.isfile(file_path):
            self._data = dataIO.load_json(file_path)
        else:
            self._data = {}
            self._save()

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

    def _create_dirs(self, file_path):
        path, _ = os.path.split(file_path)
        if path:
            try:
                os.makedirs(path)
            except FileExistsError:
                pass

    def _save(self):
        dataIO.save_json(self.path, self._data)

    def __contains__(self, item):
        return item in self._data

    def __getitem__(self, item):
        return self._data[item]

    def __len__(self):
        return len(self._data)

class ServerDB(DataDB):
    """
    A helper class to streamline the saving of server based json data
    """
    def __init__(self, *args, default_dict={}, **kwargs):
        self._default_dict = default_dict
        super().__init__(*args, **kwargs)

    def set(self, server, key, value):
        """Sets a server's entry"""
        self._set_default(server)
        self._data[server.id][key] = value
        self._save()

    def get(self, server, key, default=None):
        """Returns a server's entry"""
        self._set_default(server)
        return self._data[server.id].get(key, default)

    def remove(self, server, key):
        """Removes a server's entry"""
        self._set_default(server)
        del self._data[server.id][key]
        self._save()

    def get_all(self, server):
        """Returns all entries of a server"""
        self._set_default(server)
        return self._data[server.id]

    def remove_all(self, server):
        """Removes all entries of a server"""
        del self._data[server.id]
        self._save()

    def wipe(self):
        """Wipes all servers' data"""
        self._data = {}
        self._save()

    def all(self):
        """Returns all servers' data"""
        return self._data

    def _set_default(self, server):
        if server.id not in self._data:
            self._data[server.id] = self._default_dict.copy()
