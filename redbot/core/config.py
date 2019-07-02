import asyncio
import collections
import logging
import pickle
import weakref
from typing import (
    Any,
    Union,
    Tuple,
    Dict,
    Awaitable,
    AsyncContextManager,
    TypeVar,
    MutableMapping,
    Optional,
)

import discord

from .data_manager import cog_data_path, core_data_path
from .drivers import get_driver, IdentifierData, BackendType
from .drivers.red_base import BaseDriver

__all__ = ["Config", "get_latest_confs"]

log = logging.getLogger("red.config")

_T = TypeVar("_T")

_config_cache = weakref.WeakValueDictionary()
_retrieved = weakref.WeakSet()


def get_latest_confs() -> Tuple["Config"]:
    global _retrieved
    ret = set(_config_cache.values()) - set(_retrieved)
    _retrieved |= ret
    # noinspection PyTypeChecker
    return tuple(ret)


class _ValueCtxManager(Awaitable[_T], AsyncContextManager[_T]):  # pylint: disable=duplicate-bases
    """Context manager implementation of config values.

    This class allows mutable config values to be both "get" and "set" from
    within an async context manager.

    The context manager can only be used to get and set a mutable data type,
    i.e. `dict`s or `list`s. This is because this class's ``raw_value``
    attribute must contain a reference to the object being modified within the
    context manager.

    It should also be noted that the use of this context manager implies
    the acquisition of the value's lock.
    """

    def __init__(self, value_obj: "Value", coro):
        self.value_obj = value_obj
        self.coro = coro
        self.raw_value = None
        self.__original_value = None
        self.__lock = self.value_obj.get_lock()

    def __await__(self):
        return self.coro.__await__()

    async def __aenter__(self):
        await self.__lock.acquire()
        self.raw_value = await self
        if not isinstance(self.raw_value, (list, dict)):
            raise TypeError(
                "Type of retrieved value must be mutable (i.e. "
                "list or dict) in order to use a config value as "
                "a context manager."
            )
        self.__original_value = pickle.loads(pickle.dumps(self.raw_value, -1))
        return self.raw_value

    async def __aexit__(self, exc_type, exc, tb):
        try:
            if isinstance(self.raw_value, dict):
                raw_value = _str_key_dict(self.raw_value)
            else:
                raw_value = self.raw_value
            if raw_value != self.__original_value:
                await self.value_obj.set(self.raw_value)
        finally:
            self.__lock.release()


class Value:
    """A singular "value" of data.

    Attributes
    ----------
    identifier_data : IdentifierData
        Information on identifiers for this value.
    default
        The default value for the data element that `identifiers` points at.
    driver : `redbot.core.drivers.red_base.BaseDriver`
        A reference to `Config.driver`.

    """

    def __init__(self, identifier_data: IdentifierData, default_value, driver, config: "Config"):
        self.identifier_data = identifier_data
        self.default = default_value
        self.driver = driver
        self._config = config

    def get_lock(self) -> asyncio.Lock:
        """Get a lock to enforce atomicity with operations on this value.

        When using this lock, make sure you either use it with the
        ``async with`` syntax, or if that's not feasible, ensure you
        keep a reference to it from the acquisition to the release of
        the lock. That is, if you can't use ``async with`` syntax, use
        the lock like this::

            lock = config.foo.get_lock()
            await lock.acquire()
            # Do stuff...
            lock.release()

        Do not use it like this::

            await config.foo.get_lock().acquire()
            # Do stuff...
            config.foo.get_lock().release()

        Doing it the latter way will likely cause an error, as the
        acquired lock will be cleaned up by the garbage collector before
        it is released, meaning the second call to ``get_lock()`` will
        return a different lock to the first call.

        Returns
        -------
        asyncio.Lock
            A lock which is weakly cached for this value object.

        """
        return self._config._lock_cache.setdefault(self.identifier_data, asyncio.Lock())

    async def _get(self, default=...):
        try:
            ret = await self.driver.get(self.identifier_data)
        except KeyError:
            return default if default is not ... else self.default
        return ret

    def __call__(self, default=...) -> _ValueCtxManager[Any]:
        """Get the literal value of this data element.

        Each `Value` object is created by the `Group.__getattr__` method. The
        "real" data of the `Value` object is accessed by this method. It is a
        replacement for a :code:`get()` method.

        The return value of this method can also be used as an asynchronous
        context manager, i.e. with :code:`async with` syntax. This can only be
        used on values which are mutable (namely lists and dicts), and will
        set the value with its changes on exit of the context manager. It will
        also acquire this value's lock to ensure atomicity of operations on
        this value.

        Example
        -------
        ::

            foo = await conf.guild(some_guild).foo()

            # Is equivalent to this

            group_obj = conf.guild(some_guild)
            value_obj = group_obj.foo
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
        if isinstance(value, dict):
            value = _str_key_dict(value)
        await self.driver.set(self.identifier_data, value=value)

    async def clear(self):
        """
        Clears the value from record for the data element pointed to by `identifiers`.
        """
        await self.driver.clear(self.identifier_data)


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
        self,
        identifier_data: IdentifierData,
        defaults: dict,
        driver,
        config: "Config",
        force_registration: bool = False,
    ):
        self._defaults = defaults
        self.force_registration = force_registration
        self.driver = driver

        super().__init__(identifier_data, {}, self.driver, config)

    @property
    def defaults(self):
        return pickle.loads(pickle.dumps(self._defaults, -1))

    async def _get(self, default: Dict[str, Any] = ...) -> Dict[str, Any]:
        default = default if default is not ... else self.defaults
        raw = await super()._get(default)
        if isinstance(raw, dict):
            return self.nested_update(raw, default)
        else:
            return raw

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
        new_identifiers = self.identifier_data.add_identifier(item)
        if is_group:
            return Group(
                identifier_data=new_identifiers,
                defaults=self._defaults[item],
                driver=self.driver,
                force_registration=self.force_registration,
                config=self._config,
            )
        elif is_value:
            return Value(
                identifier_data=new_identifiers,
                default_value=self._defaults[item],
                driver=self.driver,
                config=self._config,
            )
        elif self.force_registration:
            raise AttributeError("'{}' is not a valid registered Group or value.".format(item))
        else:
            return Value(
                identifier_data=new_identifiers,
                default_value=None,
                driver=self.driver,
                config=self._config,
            )

    async def clear_raw(self, *nested_path: Any):
        """
        Allows a developer to clear data as if it was stored in a standard
        Python dictionary.

        For example::

            await conf.clear_raw("foo", "bar")

            # is equivalent to

            data = {"foo": {"bar": None}}
            del data["foo"]["bar"]

        Parameters
        ----------
        nested_path : Any
            Multiple arguments that mirror the arguments passed in for nested
            dict access. These are casted to `str` for you.
        """
        path = tuple(str(p) for p in nested_path)
        identifier_data = self.identifier_data.add_identifier(*path)
        await self.driver.clear(identifier_data)

    def is_group(self, item: Any) -> bool:
        """A helper method for `__getattr__`. Most developers will have no need
        to use this.

        Parameters
        ----------
        item : Any
            See `__getattr__`.

        """
        default = self._defaults.get(str(item))
        return isinstance(default, dict)

    def is_value(self, item: Any) -> bool:
        """A helper method for `__getattr__`. Most developers will have no need
        to use this.

        Parameters
        ----------
        item : Any
            See `__getattr__`.

        """
        try:
            default = self._defaults[str(item)]
        except KeyError:
            return False

        return not isinstance(default, dict)

    def get_attr(self, item: Union[int, str]):
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
            The name of the data field in `Config`. This is casted to
            `str` for you.

        Returns
        -------
        `Value` or `Group`
            The attribute which was requested.

        """
        if isinstance(item, int):
            item = str(item)
        return self.__getattr__(item)

    async def get_raw(self, *nested_path: Any, default=...):
        """
        Allows a developer to access data as if it was stored in a standard
        Python dictionary.

        For example::

            d = await conf.get_raw("foo", "bar")

            # is equivalent to

            data = {"foo": {"bar": "baz"}}
            d = data["foo"]["bar"]

        Note
        ----
        If retreiving a sub-group, the return value of this method will
        include registered defaults for values which have not yet been set.

        Parameters
        ----------
        nested_path : str
            Multiple arguments that mirror the arguments passed in for nested
            dict access. These are casted to `str` for you.
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
        path = tuple(str(p) for p in nested_path)

        if default is ...:
            poss_default = self.defaults
            for ident in path:
                try:
                    poss_default = poss_default[ident]
                except KeyError:
                    break
            else:
                default = poss_default

        identifier_data = self.identifier_data.add_identifier(*path)
        try:
            raw = await self.driver.get(identifier_data)
        except KeyError:
            if default is not ...:
                return default
            raise
        else:
            if isinstance(default, dict):
                return self.nested_update(raw, default)
            return raw

    def all(self) -> _ValueCtxManager[Dict[str, Any]]:
        """Get a dictionary representation of this group's data.

        The return value of this method can also be used as an asynchronous
        context manager, i.e. with :code:`async with` syntax.

        Note
        ----
        The return value of this method will include registered defaults for
        values which have not yet been set.

        Returns
        -------
        dict
            All of this Group's attributes, resolved as raw data values.

        """
        return self()

    def nested_update(
        self, current: collections.Mapping, defaults: Dict[str, Any] = ...
    ) -> Dict[str, Any]:
        """Robust updater for nested dictionaries

        If no defaults are passed, then the instance attribute 'defaults'
        will be used.
        """
        if defaults is ...:
            defaults = self.defaults

        for key, value in current.items():
            if isinstance(value, collections.Mapping):
                result = self.nested_update(value, defaults.get(key, {}))
                defaults[key] = result
            else:
                defaults[key] = pickle.loads(pickle.dumps(current[key], -1))
        return defaults

    async def set(self, value):
        if not isinstance(value, dict):
            raise ValueError("You may only set the value of a group to be a dict.")
        await super().set(value)

    async def set_raw(self, *nested_path: Any, value):
        """
        Allows a developer to set data as if it was stored in a standard
        Python dictionary.

        For example::

            await conf.set_raw("foo", "bar", value="baz")

            # is equivalent to

            data = {"foo": {"bar": None}}
            data["foo"]["bar"] = "baz"

        Parameters
        ----------
        nested_path : Any
            Multiple arguments that mirror the arguments passed in for nested
            `dict` access. These are casted to `str` for you.
        value
            The value to store.
        """
        path = tuple(str(p) for p in nested_path)
        identifier_data = self.identifier_data.add_identifier(*path)
        if isinstance(value, dict):
            value = _str_key_dict(value)
        await self.driver.set(identifier_data, value=value)


class Config:
    """Configuration manager for cogs and Red.

    You should always use `get_conf` to instantiate a Config object. Use
    `get_core_conf` for Config used in the core package.

    .. important::
        Most config data should be accessed through its respective
        group method (e.g. :py:meth:`guild`) however the process for
        accessing global data is a bit different. There is no
        :python:`global` method because global data is accessed by
        normal attribute access::

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

    def __new__(cls, cog_name, unique_identifier, *args, **kwargs):
        key = (cog_name, unique_identifier)

        if key[0] is None:
            raise ValueError("You must provide either the cog instance or a cog name.")

        if key in _config_cache:
            conf = _config_cache[key]
        else:
            conf = object.__new__(cls)
            _config_cache[key] = conf
        return conf

    def __init__(
        self,
        cog_name: str,
        unique_identifier: str,
        driver: BaseDriver,
        force_registration: bool = False,
        defaults: dict = None,
    ):
        self.cog_name = cog_name
        self.unique_identifier = unique_identifier

        self.driver = driver
        self.force_registration = force_registration
        self._defaults = defaults or {}

        self.custom_groups = {}
        self._lock_cache: MutableMapping[
            IdentifierData, asyncio.Lock
        ] = weakref.WeakValueDictionary()

    @property
    def defaults(self):
        return pickle.loads(pickle.dumps(self._defaults, -1))

    @staticmethod
    def _create_uuid(identifier: int):
        return str(identifier)

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
        if cog_instance is None and cog_name is not None:
            cog_path_override = cog_data_path(raw_name=cog_name)
        else:
            cog_path_override = cog_data_path(cog_instance=cog_instance)

        cog_name = cog_path_override.stem
        # uuid = str(hash(identifier))
        uuid = cls._create_uuid(identifier)

        # We have to import this here otherwise we have a circular dependency
        from .data_manager import basic_config

        driver_name = basic_config.get("STORAGE_TYPE", "JSON")
        driver_details = basic_config.get("STORAGE_DETAILS", {})

        driver = get_driver(
            driver_name, cog_name, uuid, data_path_override=cog_path_override, **driver_details
        )
        if driver_name == BackendType.JSON.value:
            driver.migrate_identifier(identifier)

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
        _defaults as a flat dict sounds like a good idea. May turn out
        to be an awful one but we'll see.
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
    def _update_defaults(to_add: Dict[str, Any], _partial: Dict[str, Any]):
        """
        This tries to update the _defaults dictionary with the nested
        partial dict generated by _get_defaults_dict. This WILL
        throw an error if you try to have both a value and a group
        registered under the same name.
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

    def _register_default(self, key: str, **kwargs: Any):
        if key not in self._defaults:
            self._defaults[key] = {}

        data = pickle.loads(pickle.dumps(kwargs, -1))

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

        You can do the same thing without a :python:`_defaults` dict by
        using double underscore as a variable name separator::

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

    def init_custom(self, group_identifier: str, identifier_count: int):
        """
        Initializes a custom group for usage. This method must be called first!
        """
        if group_identifier in self.custom_groups:
            raise ValueError(f"Group identifier already registered: {group_identifier}")

        self.custom_groups[group_identifier] = identifier_count

    def _get_base_group(self, category: str, *primary_keys: str) -> Group:
        is_custom = category not in (
            self.GLOBAL,
            self.GUILD,
            self.USER,
            self.MEMBER,
            self.ROLE,
            self.CHANNEL,
        )
        # noinspection PyTypeChecker
        identifier_data = IdentifierData(
            uuid=self.unique_identifier,
            category=category,
            primary_key=primary_keys,
            identifiers=(),
            custom_group_data=self.custom_groups,
            is_custom=is_custom,
        )

        pkey_len = BaseDriver.get_pkey_len(identifier_data)
        if len(primary_keys) < pkey_len:
            # Don't mix in defaults with groups higher than the document level
            defaults = {}
        else:
            defaults = self.defaults.get(category, {})
        return Group(
            identifier_data=identifier_data,
            defaults=defaults,
            driver=self.driver,
            force_registration=self.force_registration,
            config=self,
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
        return self._get_base_group(self.GUILD, str(guild.id))

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
        return self._get_base_group(self.CHANNEL, str(channel.id))

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
        return self._get_base_group(self.ROLE, str(role.id))

    def user(self, user: discord.abc.User) -> Group:
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
        return self._get_base_group(self.USER, str(user.id))

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
        return self._get_base_group(self.MEMBER, str(member.guild.id), str(member.id))

    def custom(self, group_identifier: str, *identifiers: str):
        """Returns a `Group` for the given custom group.

        Parameters
        ----------
        group_identifier : str
            Used to identify the custom group.
        identifiers : str
            The attributes necessary to uniquely identify an entry in the
            custom group. These are casted to `str` for you.

        Returns
        -------
        `Group <redbot.core.config.Group>`
            The custom group's Group object.

        """
        if group_identifier not in self.custom_groups:
            raise ValueError(f"Group identifier not initialized: {group_identifier}")
        return self._get_base_group(str(group_identifier), *map(str, identifiers))

    async def _all_from_scope(self, scope: str) -> Dict[int, Dict[Any, Any]]:
        """Get a dict of all values from a particular scope of data.

        :code:`scope` must be one of the constants attributed to
        this class, i.e. :code:`GUILD`, :code:`MEMBER` et cetera.

        IDs as keys in the returned dict are casted to `int` for convenience.

        Default values are also mixed into the data if they have not yet been
        overwritten.
        """
        group = self._get_base_group(scope)
        ret = {}
        defaults = self.defaults.get(scope, {})

        try:
            dict_ = await self.driver.get(group.identifier_data)
        except KeyError:
            pass
        else:
            for k, v in dict_.items():
                data = pickle.loads(pickle.dumps(defaults, -1))
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

    def _all_members_from_guild(self, guild_data: dict) -> dict:
        ret = {}
        defaults = self.defaults.get(self.MEMBER, {})
        for member_id, member_data in guild_data.items():
            new_member_data = pickle.loads(pickle.dumps(defaults, -1))
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
            try:
                dict_ = await self.driver.get(group.identifier_data)
            except KeyError:
                pass
            else:
                for guild_id, guild_data in dict_.items():
                    ret[int(guild_id)] = self._all_members_from_guild(guild_data)
        else:
            group = self._get_base_group(self.MEMBER, str(guild.id))
            try:
                guild_data = await self.driver.get(group.identifier_data)
            except KeyError:
                pass
            else:
                ret = self._all_members_from_guild(guild_data)
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
            # noinspection PyTypeChecker
            identifier_data = IdentifierData(
                self.unique_identifier, "", (), (), self.custom_groups
            )
            group = Group(identifier_data, defaults={}, driver=self.driver, config=self)
        else:
            cat, *scopes = scopes
            group = self._get_base_group(cat, *scopes)
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
            await self._clear_scope(self.MEMBER, str(guild.id))
            return
        await self._clear_scope(self.MEMBER)

    async def clear_all_custom(self, group_identifier: str):
        """Clear all custom group data.

        This resets all custom group data to its registered defaults.

        Parameters
        ----------
        group_identifier : str
            The identifier for the custom group. This is casted to
            `str` for you.
        """
        await self._clear_scope(str(group_identifier))

    def get_guilds_lock(self) -> asyncio.Lock:
        """Get a lock for all guild data.

        Returns
        -------
        asyncio.Lock
        """
        return self.get_custom_lock(self.GUILD)

    def get_channels_lock(self) -> asyncio.Lock:
        """Get a lock for all channel data.

        Returns
        -------
        asyncio.Lock
        """
        return self.get_custom_lock(self.CHANNEL)

    def get_roles_lock(self) -> asyncio.Lock:
        """Get a lock for all role data.

        Returns
        -------
        asyncio.Lock
        """
        return self.get_custom_lock(self.ROLE)

    def get_users_lock(self) -> asyncio.Lock:
        """Get a lock for all user data.

        Returns
        -------
        asyncio.Lock
        """
        return self.get_custom_lock(self.USER)

    def get_members_lock(self, guild: Optional[discord.Guild] = None) -> asyncio.Lock:
        """Get a lock for all member data.

        Parameters
        ----------
        guild : Optional[discord.Guild]
            The guild containing the members whose data you want to
            lock. Omit to lock all data for all members in all guilds.

        Returns
        -------
        asyncio.Lock
        """
        if guild is None:
            return self.get_custom_lock(self.GUILD)
        else:
            id_data = IdentifierData(
                self.uuid, self.MEMBER, (str(guild.id),), Tuple[str](), self.custom_groups
            )
            return self._lock_cache.setdefault(id_data, asyncio.Lock())

    def get_custom_lock(self, group_identifier: str) -> asyncio.Lock:
        """Get a lock for all data in a custom scope.

        Parameters
        ----------
        group_identifier : str
            The group identifier for the custom scope you want to lock.

        Returns
        -------
        asyncio.Lock
        """
        id_data = IdentifierData(
            self.uuid, group_identifier, Tuple[str](), Tuple[str](), self.custom_groups
        )
        return self._lock_cache.setdefault(id_data, asyncio.Lock())


def _str_key_dict(value: Dict[Any, _T]) -> Dict[str, _T]:
    """
    Recursively casts all keys in the given `dict` to `str`.

    Parameters
    ----------
    value : Dict[Any, Any]
        The `dict` to cast keys to `str`.

    Returns
    -------
    Dict[str, Any]
        The `dict` with keys (and nested keys) casted to `str`.

    """
    ret = {}
    for k, v in value.items():
        if isinstance(v, dict):
            v = _str_key_dict(v)
        ret[str(k)] = v
    return ret
