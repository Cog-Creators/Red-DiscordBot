__all__ = ["BaseDriver"]


class BaseDriver:
    def __init__(self, cog_name, identifier):
        self.cog_name = cog_name
        self.unique_cog_identifier = identifier

    @staticmethod
    def get_config_details() -> dict:
        """
        Asks users for additional configuration information necessary
        to use this config driver.

        Returns
        -------
        dict
            Dict of configuration details.

        """
        raise NotImplementedError

    async def get(self, *identifiers: str):
        """
        Finds the value indicate by the given identifiers.

        Parameters
        ----------
        *identifiers : str
            A list of identifiers that correspond to nested dict accesses.

        Returns
        -------
        Any
            Stored value.

        """
        raise NotImplementedError

    async def set(self, *identifiers: str, value=None):
        """
        Sets the value of the key indicated by the given identifiers.

        Parameters
        ----------
        *identifiers : str
            A list of identifiers that correspond to nested dict accesses.
        value
            Any JSON serializable python object.

        """
        raise NotImplementedError

    async def clear(self, *identifiers: str):
        """
        Clears out the value specified by the given identifiers.

        Equivalent to using ``del`` on a dict.

        Parameters
        ----------
        *identifiers
            A list of identifiers that correspond to nested dict accesses.

        """
        raise NotImplementedError
