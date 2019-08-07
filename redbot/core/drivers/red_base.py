import enum
from typing import Tuple

__all__ = ["BaseDriver", "IdentifierData"]


class ConfigCategory(enum.Enum):
    GLOBAL = "GLOBAL"
    GUILD = "GUILD"
    CHANNEL = "TEXTCHANNEL"
    ROLE = "ROLE"
    USER = "USER"
    MEMBER = "MEMBER"


class IdentifierData:
    def __init__(
        self,
        uuid: str,
        category: str,
        primary_key: Tuple[str, ...],
        identifiers: Tuple[str, ...],
        custom_group_data: dict,
        is_custom: bool = False,
    ):
        self._uuid = uuid
        self._category = category
        self._primary_key = primary_key
        self._identifiers = identifiers
        self.custom_group_data = custom_group_data
        self._is_custom = is_custom

    @property
    def uuid(self):
        return self._uuid

    @property
    def category(self):
        return self._category

    @property
    def primary_key(self):
        return self._primary_key

    @property
    def identifiers(self):
        return self._identifiers

    @property
    def is_custom(self):
        return self._is_custom

    def __repr__(self):
        return (
            f"<IdentifierData uuid={self.uuid} category={self.category} primary_key={self.primary_key}"
            f" identifiers={self.identifiers}>"
        )

    def __eq__(self, other) -> bool:
        if not isinstance(other, IdentifierData):
            return False
        return (
            self.uuid == other.uuid
            and self.category == other.category
            and self.primary_key == other.primary_key
            and self.identifiers == other.identifiers
        )

    def __hash__(self) -> int:
        return hash((self.uuid, self.category, self.primary_key, self.identifiers))

    def add_identifier(self, *identifier: str) -> "IdentifierData":
        if not all(isinstance(i, str) for i in identifier):
            raise ValueError("Identifiers must be strings.")

        return IdentifierData(
            self.uuid,
            self.category,
            self.primary_key,
            self.identifiers + identifier,
            self.custom_group_data,
            is_custom=self.is_custom,
        )

    def to_tuple(self):
        return tuple(
            item
            for item in (self.uuid, self.category, *self.primary_key, *self.identifiers)
            if len(item) > 0
        )


class BaseDriver:
    def __init__(self, cog_name, identifier):
        self.cog_name = cog_name
        self.unique_cog_identifier = identifier

    async def has_valid_connection(self) -> bool:
        raise NotImplementedError

    async def get(self, identifier_data: IdentifierData):
        """
        Finds the value indicate by the given identifiers.

        Parameters
        ----------
        identifier_data

        Returns
        -------
        Any
            Stored value.
        """
        raise NotImplementedError

    def get_config_details(self):
        """
        Asks users for additional configuration information necessary
        to use this config driver.

        Returns
        -------
            Dict of configuration details.
        """
        raise NotImplementedError

    async def set(self, identifier_data: IdentifierData, value=None):
        """
        Sets the value of the key indicated by the given identifiers.

        Parameters
        ----------
        identifier_data
        value
            Any JSON serializable python object.
        """
        raise NotImplementedError

    async def clear(self, identifier_data: IdentifierData):
        """
        Clears out the value specified by the given identifiers.

        Equivalent to using ``del`` on a dict.

        Parameters
        ----------
        identifier_data
        """
        raise NotImplementedError

    def _get_levels(self, category, custom_group_data):
        if category == ConfigCategory.GLOBAL.value:
            return 0
        elif category in (
            ConfigCategory.USER.value,
            ConfigCategory.GUILD.value,
            ConfigCategory.CHANNEL.value,
            ConfigCategory.ROLE.value,
        ):
            return 1
        elif category == ConfigCategory.MEMBER.value:
            return 2
        elif category in custom_group_data:
            return custom_group_data[category]
        else:
            raise RuntimeError(f"Cannot convert due to group: {category}")

    def _split_primary_key(self, category, custom_group_data, data):
        levels = self._get_levels(category, custom_group_data)
        if levels == 0:
            return (((), data),)

        def flatten(levels_remaining, currdata, parent_key=()):
            items = []
            for k, v in currdata.items():
                new_key = parent_key + (k,)
                if levels_remaining > 1:
                    items.extend(flatten(levels_remaining - 1, v, new_key).items())
                else:
                    items.append((new_key, v))
            return dict(items)

        ret = []
        for k, v in flatten(levels, data).items():
            ret.append((k, v))
        return tuple(ret)

    async def export_data(self, custom_group_data):
        categories = [c.value for c in ConfigCategory]
        categories.extend(custom_group_data.keys())

        ret = []
        for c in categories:
            ident_data = IdentifierData(
                self.unique_cog_identifier,
                c,
                (),
                (),
                custom_group_data,
                is_custom=c in custom_group_data,
            )
            try:
                data = await self.get(ident_data)
            except KeyError:
                continue
            ret.append((c, data))
        return ret

    async def import_data(self, cog_data, custom_group_data):
        for category, all_data in cog_data:
            splitted_pkey = self._split_primary_key(category, custom_group_data, all_data)
            for pkey, data in splitted_pkey:
                ident_data = IdentifierData(
                    self.unique_cog_identifier,
                    category,
                    pkey,
                    (),
                    custom_group_data,
                    is_custom=category in custom_group_data,
                )
                await self.set(ident_data, data)

    @staticmethod
    def get_pkey_len(identifier_data: IdentifierData) -> int:
        cat = identifier_data.category
        if cat == ConfigCategory.GLOBAL.value:
            return 0
        elif cat == ConfigCategory.MEMBER.value:
            return 2
        elif identifier_data.is_custom:
            return identifier_data.custom_group_data[cat]
        else:
            return 1
