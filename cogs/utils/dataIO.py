import json
import os
import logging
from shutil import copy

class InvalidFileIO(Exception):
    pass

class CorruptedJSON(Exception):
    pass

class DataIO():
    def __init__(self):
        self.logger = logging.getLogger("red")

    def save_json(self, filename, data):
        """Saves and backups json file"""
        bak_file = os.path.splitext(filename)[0]+'.bak'
        self._save_json(filename, data)
        copy(filename, bak_file) # Backup copy

    def load_json(self, filename):
        """Loads json file and restores backup copy in case of corrupted file"""
        try:
            return self._read_json(filename)
        except json.decoder.JSONDecodeError:
            result = self._restore_json(filename)
            if result:
                return self._read_json(filename) # Which hopefully will work
            else:
                raise CorruptedJSON("{} is corrupted and no backup copy is"
                                    " available.".format(filename))

    def is_valid_json(self, filename):
        """Returns True if readable json file, False if not existing.
           Tries to restore backup copy if corrupted"""
        try:
            data = self._read_json(filename)
        except FileNotFoundError:
            return False
        except json.decoder.JSONDecodeError:
            result = self._restore_json(filename)
            return result # If False, no backup copy, might as well
        else:             # allow the overwrite
            return True

    def _read_json(self, filename):
        with open(filename, encoding='utf-8', mode="r") as f:
            data = json.load(f)
        return data

    def _save_json(self, filename, data):
        with open(filename, encoding='utf-8', mode="w") as f:
            json.dump(data, f, indent=4,sort_keys=True,
                separators=(',',' : '))
        return data

    def _restore_json(self, filename):
        bak_file = os.path.splitext(filename)[0]+'.bak'
        if os.path.isfile(bak_file):
            copy(bak_file, filename) # Restore last working copy
            self.logger.warning("{} was corrupted. Restored "
                    "backup copy.".format(filename))
            return True
        else:
            self.logger.critical("{} is corrupted and there is no "
                    "backup copy available.".format(filename))
            return False

    def _legacy_fileio(self, filename, IO, data=None):
        """Old fileIO provided for backwards compatibility"""
        if IO == "save" and data != None:
            return self.save_json(filename, data)
        elif IO == "load" and data == None:
            return self.load_json(filename)
        elif IO == "check" and data == None:
            return self.is_valid_json(filename)
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

dataIO = DataIO()
fileIO = dataIO._legacy_fileio # backwards compatibility