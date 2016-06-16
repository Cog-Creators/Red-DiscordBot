import json
import os
import logging
from shutil import copy

log = logging.getLogger("red.dataIO")


class InvalidFileIO(Exception):
    pass


class CorruptedJSON(Exception):
    pass


class DataIO():
    def __init__(self, filename):
        self.filename = filename

    def save_json(self, data):
        """Saves and backups json file"""
        bak_file = os.path.splitext(self.filename)[0] + '.bak'
        self._save_json(self.filename, data)
        copy(self.filename, bak_file)  # Backup copy

    def load_json(self, filename):
        """Loads json file and restores backup copy in case of corrupted
           file"""
        try:
            return self._read_json(self.filename)
        except json.decoder.JSONDecodeError:
            result = self._restore_json(self.filename)
            if result:
                # Which hopefully will work
                return self._read_json(self.filename)
            else:
                raise CorruptedJSON("{} is corrupted and no backup copy is"
                                    " available.".format(self.filename))

    def is_valid_json(self, filename):
        """Returns True if readable json file, False if not existing.
           Tries to restore backup copy if corrupted"""
        try:
            self._read_json(self.filename)
        except FileNotFoundError:
            return False
        except json.decoder.JSONDecodeError:
            result = self._restore_json(self.filename)
            return result  # If False, no backup copy, might as well
        else:             # allow the overwrite
            return True

    def _read_json(self, filename):
        with open(self.filename, encoding='utf-8', mode="r") as f:
            data = json.load(f)
        return data

    def _save_json(self, filename, data):
        with open(self.filename, encoding='utf-8', mode="w") as f:
            json.dump(data, f, indent=4, sort_keys=True,
                      separators=(',', ' : '))
        return data

    def _restore_json(self, filename):
        bak_file = os.path.splitext(self.filename)[0] + '.bak'
        if os.path.isfile(bak_file):
            copy(bak_file, self.filename)  # Restore last working copy
            log.warning("{} was corrupted. Restored "
                        "backup copy.".format(self.filename))
            return True
        else:
            log.critical("{} is corrupted and there is no backup"
                         " copy available.".format(self.filename))
            return False


def fileIO(filename, IO, data=None):
    """Old fileIO provided for backwards compatibility"""
    config = DataIO(filename)
    if IO == "save" and data is not None:
        return config.save_json(filename, data)
    elif IO == "load" and data is None:
        return config.load_json(filename)
    elif IO == "check" and data is None:
        return config.is_valid_json(filename)
    else:
        raise InvalidFileIO("FileIO was called with invalid"
                            " parameters")


def get_value(filename, key):
    with open(filename, encoding='utf-8', mode="r") as f:
        data = json.load(f)
    return data[key]


def set_value(filename, key, value):
    data = fileIO(filename, "load")
    data[key] = value
    fileIO(filename, "save", data)
    return True
