import json
import os
import logging
from shutil import copy

log = logging.getLogger("red")


class InvalidFileIO(Exception):
    pass


class CorruptedJSON(Exception):
    pass


class DataIO:

    @classmethod
    def save_json(cls, filename, data):
        """Saves and backups json file"""
        bak_file = os.path.splitext(filename)[0] + '.bak'
        cls._save_json(filename, data)
        copy(filename, bak_file)  # Backup copy

    @classmethod
    def load_json(cls, filename):
        """Loads json file and restores backup copy in case of corrupted"""
        """ file"""
        try:
            return cls._read_json(filename)
        except json.decoder.JSONDecodeError:
            result = cls._restore_json(filename)
            if result:
                return cls._read_json(filename)  # Which hopefully will work
            else:
                raise CorruptedJSON("{} is corrupted and no backup copy is"
                                    " available.".format(filename))

    @classmethod
    def is_valid_json(cls, filename):
        """Returns True if readable json file, False if not existing.
           Tries to restore backup copy if corrupted"""
        try:
            cls._read_json(filename)
        except FileNotFoundError:
            return False
        except json.decoder.JSONDecodeError:
            result = cls._restore_json(filename)
            return result  # If False, no backup copy, might as well
        else:             # allow the overwrite
            return True

    @classmethod
    def _read_json(cls, filename):
        with open(filename, encoding='utf-8', mode="r") as f:
            data = json.load(f)
        return data

    @classmethod
    def _save_json(cls, filename, data):
        with open(filename, encoding='utf-8', mode="w") as f:
            json.dump(data, f, indent=4, sort_keys=True,
                      separators=(',', ' : '))
        return data

    @classmethod
    def _restore_json(cls, filename):
        bak_file = os.path.splitext(filename)[0] + '.bak'
        if os.path.isfile(bak_file):
            copy(bak_file, filename)  # Restore last working copy
            log.warning("{} was corrupted. Restored backup copy.".format(
                filename))
            return True
        else:
            log.critical("{} is corrupted and there is no".format(filename) +
                         " backup copy available.")
            return False

    @classmethod
    def _legacy_fileio(cls, filename, IO, data=None):
        """Old fileIO provided for backwards compatibility"""
        if IO == "save" and data is not None:
            return cls.save_json(filename, data)
        elif IO == "load" and data is None:
            return cls.load_json(filename)
        elif IO == "check" and data is None:
            return cls.is_valid_json(filename)
        else:
            raise InvalidFileIO("FileIO was called with invalid"
                                " parameters")


dataIO = DataIO
fileIO = dataIO._legacy_fileio  # backwards compatibility


def get_value(filename, key):
    data = dataIO.load_json(filename)
    return data[key]


def set_value(filename, key, value):
    data = dataIO.load_json(filename)
    data[key] = value
    dataIO.save_json(filename, data)
    return True
