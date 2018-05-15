import json
from pathlib import Path
from redbot.core import Config


class DataConverter:
    """
    Class for moving v2 data to v3
    """

    def __init__(self, config_instance: Config):
        self.config = config_instance

    @staticmethod
    def json_load(file_path: Path):
        """Utility function for quickly grabbing data from a JSON file

        Parameters
        ----------
        file_path: `pathlib.Path`
            The path to the file to grabdata from

        Raises
        ------
        FileNotFoundError
            The file doesn't exist
        json.JsonDecodeError
            The file isn't valid JSON
        """
        try:
            with file_path.open(mode="r", encoding="utf-8") as f:
                data = json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            raise
        else:
            return data

    async def convert(self, file_path: Path, conversion_spec: object):
        """Converts v2 data to v3 format. If your v2 data uses multiple files
        you will need to call this for each file.

        Parameters
        ----------
        file_path : `pathlib.Path`
            This should be the path to a JSON settings file from v2
        conversion_spec : `object`
            This should be a function which takes a single argument argument
            (the loaded JSON) and from it either
            returns or yields one or more `dict`
            whose items are in the form::

                {(SCOPE, *IDENTIFIERS): {(key_tuple): value}}

            an example of a possible entry of that dict::

                {(Config.MEMBER, '133049272517001216', '78631113035100160'):
                    {('balance',): 9001}}


            This allows for any amount of entries at each level
            in each of the nested dictionaries returned by conversion_spec
            but the nesting cannot be different to this and still get the
            expected results
            see documentation for Config for more details on scopes
            and the identifiers they need

        Returns
        -------
        None

        Raises
        ------
        FileNotFoundError
            No such file at the specified path
        json.JSONDecodeError
            File is not valid JSON
        AttributeError
            Something goes wrong with your conversion and it provides
            data in the wrong format
        """

        v2data = self.json_load(file_path)

        for entryset in conversion_spec(v2data):
            for scope_id, values in entryset.items():
                base = self.config._get_base_group(*scope_id)
                for inner_k, inner_v in values.items():
                    await base.set_raw(*inner_k, value=inner_v)

    async def dict_import(self, entrydict: dict):
        """This imports a dictionary in the correct format into Config

        Parameters
        ----------
        entrydict : `dict`
            This should be a dictionary of values to set.
            This is provided as an alternative
            to providing a file and conversion specification
            the dictionary should be in the following format::

                {(SCOPE, *IDENTIFIERS): {(key_tuple): value}}`

            an example of a possible entry of that dict::

                {(Config.MEMBER, '133049272517001216', '78631113035100160'):
                    {('balance',): 9001}}

            This allows for any amount of entries at each level
            in each of the nested dictionaries returned by conversion_spec
            but the nesting cannot be different to this and still get the
            expected results

        Returns
        -------
        None

        Raises
        ------
        AttributeError
            Data not in the correct format.
        """

        for scope_id, values in entrydict.items():
            base = self.config._get_base_group(*scope_id)
            for inner_k, inner_v in values.items():
                await base.set_raw(*inner_k, value=inner_v)
