import logging
import collections
from copy import deepcopy
from typing import Union, Tuple, TYPE_CHECKING

import discord

from .data_manager import cog_data_path, core_data_path
from .drivers import get_driver

if TYPE_CHECKING:
    from .drivers.red_base import BaseDriver

log = logging.getLogger("red.config")


class _ValueCtxManager:
    """Context manager implementation of config values.

    This class allows mutable config values to be both "get" and "set" from
    within an async context manager.

    The context manager can only be used to get and set a mutable data type,
    i.e. `dict`s or `list`s. This is because this class's ``raw_value``
    attribute must contain a reference to the object being modified within the
    context manager.
    """

    def __init__(self, value_obj, coro):
        self.value_obj = value_obj
        self.coro = coro

    def __await__(self):
        return self.coro.__await__()

    async def __aenter__(self):
        self.raw_value = await self
        if not isinstance(self.raw_value, (list, dict)):
            raise TypeError(
                "Type of retrieved value must be mutable (i.e. "
                "list or dict) in order to use a config value as "
                "a context manager."
            )
        return self.raw_value

    async def __aexit__(self, *exc_info):
        await self.value_obj.set(self.raw_value)


class Value:
    """A singular "value" of data.

    Attributes
    ----------
    identifiers : `tuple` of `str`
        This attribute provides all the keys necessary to get a specific data
        element from a json document.
    default
        The default value for the data element that `identifiers` points at.
    driver : `redbot.core.drivers.red_base.BaseDriver`
        A reference to `Config.driver`.

    """

    def __init__(self, identifiers: Tuple[str], default_value, driver):
        self._identifiers = identifiers
        self.default = default_value

        self.driver = driver

    @property
    def identifiers(self):
        return tuple(str(i) for i in self._identifiers)

    async def _get(self, default):
        try:
            ret = await self.driver.get(*self.identifiers)
        except KeyError:
            return default if default is not None else self.default
        return ret

    def __call__(self, default=None):
        """Get the literal value of this data element.

        Each `Value` object is created by the `Group.__getattr__` method. The
        "real" data of the `Value` object is accessed by this method. It is a
        replacement for a :code:`get()` method.

        The return value of this method can also be used as an asynchronous
        context manager, i.e. with :code:`async with` syntax. This can only be
        used on values which are mutable (namely lists and dicts), and will
        set the value with its changes on exit of the context manager.

        Example
        -------
        ::

            foo = await conf.guild(some_guild).foo()

            # Is equivalent to this

            group_obj = conf.guild(some_guild)
            value_obj = conf.foo
            foo = await value_obj()

        .. important::

            This is now, for all intents and purposes, a coroutine.

        Parameters
        ----------
        default : `object`, optional
            This argument acts as an override for the registered default
            provided by `default`. This argument is ignored if its
            value is :code:`None`.

        Returns
        -------
        `awaitable` mixed with `asynchronous context manager`
            A coroutine object mixed in with an async context manager. When
            awaited, this returns the raw data value. When used in :code:`async
            with` syntax, on gets the value on entrance, and sets it on exit.

        """
        return _ValueCtxManager(self, self._get(default))

    async def set(self, value):
        """Set the value of the data elements pointed to by `identifiers`.

        Example
        -------
        ::

            # Sets global value "foo" to False
            await conf.foo.set(False)

            # Sets guild specific value of "bar" to True
            await conf.guild(some_guild).bar.set(True)

        Parameters
        ----------
        value
            The new literal value of this attribute.

        """
        await self.driver.set(*self.identifiers, value=value)

    async def clear(self):
        """
        Clears the value from record for the data element pointed to by `identifiers`.
        """
        await self.driver.clear(*self.identifiers)


class Group(Value):
    """
    Represents a group of data, composed of more `Group` or `Value` objects.

    Inherits from `Value` which means that all of the attributes and methods
    available in `Value` are also available when working with a `Group` object.

    Attributes
    ----------
    defaults : `dict`
        All registered default values for this Group.
    force_registration : `bool`
        Same as `Config.force_registration`.
    driver : `redbot.core.drivers.red_base.BaseDriver`
        A reference to `Config.driver`.

    """

    def __init__(
        self, identifiers: Tuple[str], defaults: dict, driver, force_registration: bool = False
    ):
        self._defaults = defaults
        self.force_registration = force_registration
        self.driver = driver

        super().__init__(identifiers, {}, self.driver)

    @property
    def defaults(self):
        return deepcopy(self._defaults)

    # noinspection PyTypeChecker
    def __getattr__(self, item: str) -> Union["Group", Value]:
        """Get an attribute of this group.

        This special method is called whenever dot notation is used on this
        object.

        Parameters
        ----------
        item : str
            The name of the attribute being accessed.

        Returns
        -------
        `Group` or `Value`
            A child value of this Group. This, of course, can be another
            `Group`, due to Config's composite pattern.

        Raises
        ------
        AttributeError
            If the attribute has not been registered and `force_registration`
            is set to :code:`True`.

        """
        is_group = self.is_group(item)
        is_value = not is_group and self.is_value(item)
        new_identifiers = self.identifiers + (item,)
        if is_group:
            return Group(
                identifiers=new_identifiers,
                defaults=self._defaults[item],
                driver=self.driver,
                force_registration=self.force_registration,
            )
        elif is_value:
            return Value(
                identifiers=new_identifiers, default_value=self._defaults[item], driver=self.driver
            )
        elif self.force_registration:
            raise AttributeError("'{}' is not a valid registered Group or value.".format(item))
        else:
            return Value(identifiers=new_identifiers, default_value=None, driver=self.driver)

    def is_group(self, item: str) -> bool:
        """A helper method for `__getattr__`. Most developers will have no need
        to use this.

        Parameters
        ----------
        item : str
            See `__getattr__`.

        """
        default = self._defaults.get(item)
        return isinstance(default, dict)

    def is_value(self, item: str) -> bool:
        """A helper method for `__getattr__`. Most developers will have no need
        to use this.

        Parameters
        ----------
        item : str
            See `__getattr__`.

        """
        try:
            default = self._defaults[item]
        except KeyError:
            return False

        return not isinstance(default, dict)

    def get_attr(self, item: str):
        """Manually get an attribute of this Group.

        This is available to use as an alternative to using normal Python
        attribute access. It may be required if you find a need for dynamic
        attribute access.

        Example
        -------
        A possible use case::

            @commands.command()
            async def some_command(self, ctx, item: str):
                user = ctx.author

                # Where the value of item is the name of the data field in Config
                await ctx.send(await self.conf.user(user).get_attr(item).foo())

        Parameters
        ----------
        item : str
            The name of the data field in `Config`.

        Returns
        -------
        `Value` or `Group`
            The attribute which was requested.

        """
        return self.__getattr__(item)

    async def get_raw(self, *nested_path: str, default=...):
        """
        Allows a developer to access data as if it was stored in a standard
        Python dictionary.

        For example::

            d = await conf.get_raw("foo", "bar")

            # is equivalent to

            data = {"foo": {"bar": "baz"}}
            d = data["foo"]["bar"]

        Parameters
        ----------
        nested_path : str
            Multiple arguments that mirror the arguments passed in for nested
            dict access.
        default
            Default argument for the value attempting to be accessed. If the
            value does not exist the default will be returned.

        Returns
        -------
        Any
            The value of the path requested.

        Raises
        ------
        KeyError
            If the value does not exist yet in Config's internal storage.

        """
        path = [str(p) for p in nested_path]

        if default is ...:
            poss_default = self.defaults
            for ident in path:
                try:
                    poss_default = poss_default[ident]
                except KeyError:
                    break
            else:
                default = poss_default

        try:
            return await self.driver.get(*self.identifiers, *path)
        except KeyError:
            if default is not ...:
                return default
            raise

    async def all(self) -> dict:
        """Get a dictionary representation of this group's data.

        Note
        ----
        The return value of this method will include registered defaults for
        values which have not yet been set.

        Returns
        -------
        dict
            All of this Group's attributes, resolved as raw data values.

        """
        return self.nested_update(await self())

    def nested_update(self, current, defaults=None):
        """Robust updater for nested dictionaries

        If no defaults are passed, then the instance attribute 'defaults'
        will be used.

        """
        if not defaults:
            defaults = self.defaults

        for key, value in current.items():
            if isinstance(value, collections.Mapping):
                result = self.nested_update(value, defaults.get(key, {}))
                defaults[key] = result
            else:
                defaults[key] = deepcopy(current[key])
        return defaults

    async def set(self, value):
        if not isinstance(value, dict):
            raise ValueError("You may only set the value of a group to be a dict.")
        await super().set(value)

    async def set_raw(self, *nested_path: str, value):
        """
        Allows a developer to set data as if it was stored in a standard
        Python dictionary.

        For example::

            await conf.set_raw("foo", "bar", value="baz")

            # is equivalent to

            data = {"foo": {"bar": None}}
            d["foo"]["bar"] = "baz"

        Parameters
        ----------
        nested_path : str
            Multiple arguments that mirror the arguments passed in for nested
            dict access.
        value
            The value to store.
        """
        path = [str(p) for p in nested_path]
        await self.driver.set(*self.identifiers, *path, value=value)


class Config:
    """Configuration manager for cogs and Red.

    You should always use `get_conf` or to instantiate a Config object. Use
    `get_core_conf` for Config used in the core package.

    .. important::
        Most config data should be accessed through its respective group method (e.g. :py:meth:`guild`)
        however the process for accessing global data is a bit different. There is no :python:`global` method
        because global data is accessed by normal attribute access::

            await conf.foo()

    Attributes
    ----------
    cog_name : `str`
        The name of the cog that has requested a `Config` object.
    unique_identifier : `int`
        Unique identifier provided to differentiate cog data when name
        conflicts occur.
    driver
        An instance of a driver that implements `redbot.core.drivers.red_base.BaseDriver`.
    force_registration : `bool`
        Determines if Config should throw an error if a cog attempts to access
        an attribute which has not been previously registered.

        Note
        ----
        **You should use this.** By enabling force registration you give Config
        the ability to alert you instantly if you've made a typo when
        attempting to access data.

    """

    GLOBAL = "GLOBAL"
    GUILD = "GUILD"
    CHANNEL = "TEXTCHANNEL"
    ROLE = "ROLE"
    USER = "USER"
    MEMBER = "MEMBER"

    def __init__(
        self,
        cog_name: str,
        unique_identifier: str,
        driver: "BaseDriver",
        force_registration: bool = False,
        defaults: dict = None,
    ):
        self.cog_name = cog_name
        self.unique_identifier = unique_identifier

        self.driver = driver
        self.force_registration = force_registration
        self._defaults = defaults or {}

    @property
    def defaults(self):
        return deepcopy(self._defaults)

    @classmethod
    def get_conf(cls, cog_instance, identifier: int, force_registration=False, cog_name=None):
        """Get a Config instance for your cog.

        .. warning::

            If you are using this classmethod to get a second instance of an
            existing Config object for a particular cog, you MUST provide the
            correct identifier. If you do not, you *will* screw up all other
            Config instances for that cog.

        Parameters
        ----------
        cog_instance
            This is an instance of your cog after it has been instantiated. If
            you're calling this method from within your cog's :code:`__init__`,
            this is just :code:`self`.
        identifier : int
            A (hard-coded) random integer, used to keep your data distinct from
            any other cog with the same name.
        force_registration : `bool`, optional
            Should config require registration of data keys before allowing you
            to get/set values? See `force_registration`.
        cog_name : str, optional
            Config normally uses ``cog_instance`` to determine tha name of your cog.
            If you wish you may pass ``None`` to ``cog_instance`` and directly specify
            the name of your cog here.

        Returns
        -------
        Config
            A new Config object.

        """
        if cog_instance is None and not cog_name is None:
            cog_path_override = cog_data_path(raw_name=cog_name)
        else:
            cog_path_override = cog_data_path(cog_instance=cog_instance)

        cog_name = cog_path_override.stem
        uuid = str(hash(identifier))

        # We have to import this here otherwise we have a circular dependency
        from .data_manager import basic_config

        log.debug("Basic config: \n\n{}".format(basic_config))

        driver_name = basic_config.get("STORAGE_TYPE", "JSON")
        driver_details = basic_config.get("STORAGE_DETAILS", {})

        log.debug("Using driver: '{}'".format(driver_name))

        driver = get_driver(
            driver_name, cog_name, uuid, data_path_override=cog_path_override, **driver_details
        )
        conf = cls(
            cog_name=cog_name,
            unique_identifier=uuid,
            force_registration=force_registration,
            driver=driver,
        )
        return conf

    @classmethod
    def get_core_conf(cls, force_registration: bool = False):
        """Get a Config instance for a core module.

        All core modules that require a config instance should use this
        classmethod instead of `get_conf`.

        Parameters
        ----------
        force_registration : `bool`, optional
            See `force_registration`.

        """
        core_path = core_data_path()

        # We have to import this here otherwise we have a circular dependency
        from .data_manager import basic_config

        driver_name = basic_config.get("STORAGE_TYPE", "JSON")
        driver_details = basic_config.get("STORAGE_DETAILS", {})

        driver = get_driver(
            driver_name, "Core", "0", data_path_override=core_path, **driver_details
        )
        conf = cls(
            cog_name="Core",
            driver=driver,
            unique_identifier="0",
            force_registration=force_registration,
        )
        return conf

    def __getattr__(self, item: str) -> Union[Group, Value]:
        """Same as `group.__getattr__` except for global data.

        Parameters
        ----------
        item : str
            The attribute you want to get.

        Returns
        -------
        `Group` or `Value`
            The value for the attribute you want to retrieve

        Raises
        ------
        AttributeError
            If there is no global attribute by the given name and
            `force_registration` is set to :code:`True`.
        """
        global_group = self._get_base_group(self.GLOBAL)
        return getattr(global_group, item)

    @staticmethod
    def _get_defaults_dict(key: str, value) -> dict:
        """
        Since we're allowing nested config stuff now, not storing the
            _defaults as a flat dict sounds like a good idea. May turn
            out to be an awful one but we'll see.
        :param key:
        :param value:
        :return:
        """
        ret = {}
        partial = ret
        splitted = key.split("__")
        for i, k in enumerate(splitted, start=1):
            if not k.isidentifier():
                raise RuntimeError("'{}' is an invalid config key.".format(k))
            if i == len(splitted):
                partial[k] = value
            else:
                partial[k] = {}
                partial = partial[k]
        return ret

    @staticmethod
    def _update_defaults(to_add: dict, _partial: dict):
        """
        This tries to update the _defaults dictionary with the nested
            partial dict generated by _get_defaults_dict. This WILL
            throw an error if you try to have both a value and a group
            registered under the same name.
        :param to_add:
        :param _partial:
        :return:
        """
        for k, v in to_add.items():
            val_is_dict = isinstance(v, dict)
            if k in _partial:
                existing_is_dict = isinstance(_partial[k], dict)
                if val_is_dict != existing_is_dict:
                    # != is XOR
                    raise KeyError("You cannot register a Group and a Value under the same name.")
                if val_is_dict:
                    Config._update_defaults(v, _partial=_partial[k])
                else:
                    _partial[k] = v
            else:
                _partial[k] = v

    def _register_default(self, key: str, **kwargs):
        if key not in self._defaults:
            self._defaults[key] = {}

        data = deepcopy(kwargs)

        for k, v in data.items():
            to_add = self._get_defaults_dict(k, v)
            self._update_defaults(to_add, self._defaults[key])

    def register_global(self, **kwargs):
        """Register default values for attributes you wish to store in `Config`
        at a global level.

        Examples
        --------
        You can register a single value or multiple values::

            conf.register_global(
                foo=True
            )

            conf.register_global(
                bar=False,
                baz=None
            )

        You can also now register nested values::

            _defaults = {
                "foo": {
                    "bar": True,
                    "baz": False
                }
            }

            # Will register `foo.bar` == True and `foo.baz` == False
            conf.register_global(
                **_defaults
            )

        You can do the same thing without a :python:`_defaults` dict by using double underscore as a variable
        name separator::

            # This is equivalent to the previous example
            conf.register_global(
                foo__bar=True,
                foo__baz=False
            )

        """
        self._register_default(self.GLOBAL, **kwargs)

    def register_guild(self, **kwargs):
        """Register default values on a per-guild level.

        See `register_global` for more details.
        """
        self._register_default(self.GUILD, **kwargs)

    def register_channel(self, **kwargs):
        """Register default values on a per-channel level.

        See `register_global` for more details.
        """
        # We may need to add a voice channel category later
        self._register_default(self.CHANNEL, **kwargs)

    def register_role(self, **kwargs):
        """Registers default values on a per-role level.

        See `register_global` for more details.
        """
        self._register_default(self.ROLE, **kwargs)

    def register_user(self, **kwargs):
        """Registers default values on a per-user level.

        This means that each user's data is guild-independent.

        See `register_global` for more details.
        """
        self._register_default(self.USER, **kwargs)

    def register_member(self, **kwargs):
        """Registers default values on a per-member level.

        This means that each user's data is guild-dependent.

        See `register_global` for more details.
        """
        self._register_default(self.MEMBER, **kwargs)

    def register_custom(self, group_identifier: str, **kwargs):
        """Registers default values for a custom group.

        See `register_global` for more details.
        """
        self._register_default(group_identifier, **kwargs)

    def _get_base_group(self, key: str, *identifiers: str) -> Group:
        # noinspection PyTypeChecker
        return Group(
            identifiers=(key, *identifiers),
            defaults=self.defaults.get(key, {}),
            driver=self.driver,
            force_registration=self.force_registration,
        )

    def guild(self, guild: discord.Guild) -> Group:
        """Returns a `Group` for the given guild.

        Parameters
        ----------
        guild : discord.Guild
            A guild object.

        Returns
        -------
        `Group <redbot.core.config.Group>`
            The guild's Group object.

        """
        return self._get_base_group(self.GUILD, guild.id)

    def channel(self, channel: discord.TextChannel) -> Group:
        """Returns a `Group` for the given channel.

        This does not discriminate between text and voice channels.

        Parameters
        ----------
        channel : `discord.abc.GuildChannel`
            A channel object.

        Returns
        -------
        `Group <redbot.core.config.Group>`
            The channel's Group object.

        """
        return self._get_base_group(self.CHANNEL, channel.id)

    def role(self, role: discord.Role) -> Group:
        """Returns a `Group` for the given role.

        Parameters
        ----------
        role : discord.Role
            A role object.

        Returns
        -------
        `Group <redbot.core.config.Group>`
            The role's Group object.

        """
        return self._get_base_group(self.ROLE, role.id)

    def user(self, user: discord.User) -> Group:
        """Returns a `Group` for the given user.

        Parameters
        ----------
        user : discord.User
            A user object.

        Returns
        -------
        `Group <redbot.core.config.Group>`
            The user's Group object.

        """
        return self._get_base_group(self.USER, user.id)

    def member(self, member: discord.Member) -> Group:
        """Returns a `Group` for the given member.

        Parameters
        ----------
        member : discord.Member
            A member object.

        Returns
        -------
        `Group <redbot.core.config.Group>`
            The member's Group object.
        """
        return self._get_base_group(self.MEMBER, member.guild.id, member.id)

    def custom(self, group_identifier: str, *identifiers: str):
        """Returns a `Group` for the given custom group.

        Parameters
        ----------
        group_identifier : str
            Used to identify the custom group.

        identifiers : str
            The attributes necessary to uniquely identify an entry in the
            custom group.

        Returns
        -------
        `Group <redbot.core.config.Group>`
            The custom group's Group object.
        """
        return self._get_base_group(group_identifier, *identifiers)

    async def _all_from_scope(self, scope: str):
        """Get a dict of all values from a particular scope of data.

        :code:`scope` must be one of the constants attributed to
        this class, i.e. :code:`GUILD`, :code:`MEMBER` et cetera.

        IDs as keys in the returned dict are casted to `int` for convenience.

        Default values are also mixed into the data if they have not yet been
        overwritten.
        """
        group = self._get_base_group(scope)
        dict_ = await group()
        ret = {}
        for k, v in dict_.items():
            data = group.defaults
            data.update(v)
            ret[int(k)] = data
        return ret

    async def all_guilds(self) -> dict:
        """Get all guild data as a dict.

        Note
        ----
        The return value of this method will include registered defaults for
        values which have not yet been set.

        Returns
        -------
        dict
            A dictionary in the form {`int`: `dict`} mapping
            :code:`GUILD_ID -> data`.

        """
        return await self._all_from_scope(self.GUILD)

    async def all_channels(self) -> dict:
        """Get all channel data as a dict.

        Note
        ----
        The return value of this method will include registered defaults for
        values which have not yet been set.

        Returns
        -------
        dict
            A dictionary in the form {`int`: `dict`} mapping
            :code:`CHANNEL_ID -> data`.

        """
        return await self._all_from_scope(self.CHANNEL)

    async def all_roles(self) -> dict:
        """Get all role data as a dict.

        Note
        ----
        The return value of this method will include registered defaults for
        values which have not yet been set.

        Returns
        -------
        dict
            A dictionary in the form {`int`: `dict`} mapping
            :code:`ROLE_ID -> data`.

        """
        return await self._all_from_scope(self.ROLE)

    async def all_users(self) -> dict:
        """Get all user data as a dict.

        Note
        ----
        The return value of this method will include registered defaults for
        values which have not yet been set.

        Returns
        -------
        dict
            A dictionary in the form {`int`: `dict`} mapping
            :code:`USER_ID -> data`.

        """
        return await self._all_from_scope(self.USER)

    def _all_members_from_guild(self, group: Group, guild_data: dict) -> dict:
        ret = {}
        for member_id, member_data in guild_data.items():
            new_member_data = group.defaults
            new_member_data.update(member_data)
            ret[int(member_id)] = new_member_data
        return ret

    async def all_members(self, guild: discord.Guild = None) -> dict:
        """Get data for all members.

        If :code:`guild` is specified, only the data for the members of that
        guild will be returned. As such, the dict will map
        :code:`MEMBER_ID -> data`. Otherwise, the dict maps
        :code:`GUILD_ID -> MEMBER_ID -> data`.

        Note
        ----
        The return value of this method will include registered defaults for
        values which have not yet been set.

        Parameters
        ----------
        guild : `discord.Guild`, optional
            The guild to get the member data from. Can be omitted if data
            from every member of all guilds is desired.

        Returns
        -------
        dict
            A dictionary of all specified member data.

        """
        ret = {}
        if guild is None:
            group = self._get_base_group(self.MEMBER)
            dict_ = await group()
            for guild_id, guild_data in dict_.items():
                ret[int(guild_id)] = self._all_members_from_guild(group, guild_data)
        else:
            group = self._get_base_group(self.MEMBER, guild.id)
            guild_data = await group()
            ret = self._all_members_from_guild(group, guild_data)
        return ret

    async def _clear_scope(self, *scopes: str):
        """Clear all data in a particular scope.

        The only situation where a second scope should be passed in is if
        member data from a specific guild is being cleared.

        If no scopes are passed, then all data is cleared from every scope.

        Parameters
        ----------
        *scopes : str, optional
            The scope of the data. Generally only one scope needs to be
            provided, a second only necessary for clearing member data
            of a specific guild.

            **Leaving blank removes all data from this Config instance.**

        """
        if not scopes:
            group = Group(identifiers=[], defaults={}, driver=self.driver)
        else:
            group = self._get_base_group(*scopes)
        await group.clear()

    async def clear_all(self):
        """Clear all data from this Config instance.

        This resets all data to its registered defaults.

        .. important::

            This cannot be undone.

        """
        await self._clear_scope()

    async def clear_all_globals(self):
        """Clear all global data.

        This resets all global data to its registered defaults.
        """
        await self._clear_scope(self.GLOBAL)

    async def clear_all_guilds(self):
        """Clear all guild data.

        This resets all guild data to its registered defaults.
        """
        await self._clear_scope(self.GUILD)

    async def clear_all_channels(self):
        """Clear all channel data.

        This resets all channel data to its registered defaults.
        """
        await self._clear_scope(self.CHANNEL)

    async def clear_all_roles(self):
        """Clear all role data.

        This resets all role data to its registered defaults.
        """
        await self._clear_scope(self.ROLE)

    async def clear_all_users(self):
        """Clear all user data.

        This resets all user data to its registered defaults.
        """
        await self._clear_scope(self.USER)

    async def clear_all_members(self, guild: discord.Guild = None):
        """Clear all member data.

        This resets all specified member data to its registered defaults.

        Parameters
        ----------
        guild : `discord.Guild`, optional
            The guild to clear member data from. Omit to clear member data from
            all guilds.

        """
        if guild is not None:
            await self._clear_scope(self.MEMBER, guild.id)
            return
        await self._clear_scope(self.MEMBER)

    async def clear_all_custom(self, group_identifier: str):
        """Clear all custom group data.

        This resets all custom group data to its registered defaults.
        """
        await self._clear_scope(group_identifier)
