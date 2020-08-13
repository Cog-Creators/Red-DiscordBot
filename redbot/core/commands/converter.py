"""
commands.converter
==================
This module contains useful functions and classes for command argument conversion.

Some of the converters within are included provisionaly and are marked as such.
"""
import functools
import re
import warnings
from datetime import timedelta
from typing import (
    TYPE_CHECKING,
    Generic,
    Optional,
    Optional as NoParseOptional,
    Tuple,
    List,
    Dict,
    Type,
    TypeVar,
    Literal as Literal,
    Any,
    Union as UserInputOptional,
)

import discord
from discord.ext import commands as dpy_commands
from discord.ext.commands import BadArgument

from ..i18n import Translator
from ..utils.chat_formatting import humanize_timedelta, humanize_list

if TYPE_CHECKING:
    from .context import Context

__all__ = [
    "DictConverter",
    "GuildConverter",
    "UserInputOptional",
    "NoParseOptional",
    "TimedeltaConverter",
    "get_dict_converter",
    "get_timedelta_converter",
    "parse_timedelta",
    "Literal",
]

_ = Translator("commands.converter", __file__)

ID_REGEX = re.compile(r"([0-9]{15,21})")


# Taken with permission from
# https://github.com/mikeshardmind/SinbadCogs/blob/816f3bc2ba860243f75112904b82009a8a9e1f99/scheduler/time_utils.py#L9-L19
TIME_RE_STRING = r"\s?".join(
    [
        r"((?P<weeks>\d+?)\s?(weeks?|w))?",
        r"((?P<days>\d+?)\s?(days?|d))?",
        r"((?P<hours>\d+?)\s?(hours?|hrs|hr?))?",
        r"((?P<minutes>\d+?)\s?(minutes?|mins?|m(?!o)))?",  # prevent matching "months"
        r"((?P<seconds>\d+?)\s?(seconds?|secs?|s))?",
    ]
)

TIME_RE = re.compile(TIME_RE_STRING, re.I)


def parse_timedelta(
    argument: str,
    *,
    maximum: Optional[timedelta] = None,
    minimum: Optional[timedelta] = None,
    allowed_units: Optional[List[str]] = None,
) -> Optional[timedelta]:
    """
    This converts a user provided string into a timedelta

    The units should be in order from largest to smallest. 
    This works with or without whitespace.

    Parameters
    ----------
    argument : str
        The user provided input
    maximum : Optional[timedelta]
        If provided, any parsed value higher than this will raise an exception
    minimum : Optional[timedelta]
        If provided, any parsed value lower than this will raise an exception
    allowed_units : Optional[List[str]]
        If provided, you can constrain a user to expressing the amount of time
        in specific units. The units you can chose to provide are the same as the
        parser understands. (``weeks``, ``days``, ``hours``, ``minutes``, ``seconds``)

    Returns
    -------
    Optional[timedelta]
        If matched, the timedelta which was parsed. This can return `None`

    Raises
    ------
    BadArgument
        If the argument passed uses a unit not allowed, but understood
        or if the value is out of bounds.
    """
    matches = TIME_RE.match(argument)
    allowed_units = allowed_units or ["weeks", "days", "hours", "minutes", "seconds"]
    if matches:
        params = {k: int(v) for k, v in matches.groupdict().items() if v is not None}
        for k in params.keys():
            if k not in allowed_units:
                raise BadArgument(
                    _("`{unit}` is not a valid unit of time for this command").format(unit=k)
                )
        if params:
            delta = timedelta(**params)
            if maximum and maximum < delta:
                raise BadArgument(
                    _(
                        "This amount of time is too large for this command. (Maximum: {maximum})"
                    ).format(maximum=humanize_timedelta(timedelta=maximum))
                )
            if minimum and delta < minimum:
                raise BadArgument(
                    _(
                        "This amount of time is too small for this command. (Minimum: {minimum})"
                    ).format(minimum=humanize_timedelta(timedelta=minimum))
                )
            return delta
    return None


class GuildConverter(discord.Guild):
    """Converts to a `discord.Guild` object.

    The lookup strategy is as follows (in order):

    1. Lookup by ID.
    2. Lookup by name.
    """

    @classmethod
    async def convert(cls, ctx: "Context", argument: str) -> discord.Guild:
        match = ID_REGEX.fullmatch(argument)

        if match is None:
            ret = discord.utils.get(ctx.bot.guilds, name=argument)
        else:
            guild_id = int(match.group(1))
            ret = ctx.bot.get_guild(guild_id)

        if ret is None:
            raise BadArgument(_('Server "{name}" not found.').format(name=argument))

        return ret


class _APIToken(discord.ext.commands.Converter):
    """Converts to a `dict` object.

    This will parse the input argument separating the key value pairs into a 
    format to be used for the core bots API token storage.
    
    This will split the argument by a space, comma, or semicolon and return a dict
    to be stored. Since all API's are different and have different naming convention,
    this leaves the onus on the cog creator to clearly define how to setup the correct
    credential names for their cogs.

    Note: Core usage of this has been replaced with `DictConverter` use instead.

    .. warning::
        This will be removed in the first minor release after 2020-08-05.
    """

    async def convert(self, ctx: "Context", argument) -> dict:
        bot = ctx.bot
        result = {}
        match = re.split(r";|,| ", argument)
        # provide two options to split incase for whatever reason one is part of the api key we're using
        if len(match) > 1:
            result[match[0]] = "".join(r for r in match[1:])
        else:
            raise BadArgument(_("The provided tokens are not in a valid format."))
        if not result:
            raise BadArgument(_("The provided tokens are not in a valid format."))
        return result


_APIToken.__name__ = "APIToken"


def __getattr__(name: str, *, stacklevel: int = 2) -> Any:
    # honestly, this is awesome (PEP-562)
    if name == "APIToken":
        warnings.warn(
            "`APIToken` is deprecated since Red 3.3.0 and will be removed"
            " in the first minor release after 2020-08-05. Use `DictConverter` instead.",
            DeprecationWarning,
            stacklevel=stacklevel,
        )
        return globals()["_APIToken"]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> List[str]:
    return [*globals().keys(), "APIToken"]


# Below this line are a lot of lies for mypy about things that *end up* correct when
# These are used for command conversion purposes. Please refer to the portion
# which is *not* for type checking for the actual implementation
# and ensure the lies stay correct for how the object should look as a typehint

if TYPE_CHECKING:
    DictConverter = Dict[str, str]
else:

    class DictConverter(dpy_commands.Converter):
        """
        Converts pairs of space seperated values to a dict
        """

        def __init__(self, *expected_keys: str, delims: Optional[List[str]] = None):
            self.expected_keys = expected_keys
            self.delims = delims or [" "]
            self.pattern = re.compile(r"|".join(re.escape(d) for d in self.delims))

        async def convert(self, ctx: "Context", argument: str) -> Dict[str, str]:
            ret: Dict[str, str] = {}
            args = self.pattern.split(argument)

            if len(args) % 2 != 0:
                raise BadArgument()

            iterator = iter(args)

            for key in iterator:
                if self.expected_keys and key not in self.expected_keys:
                    raise BadArgument(_("Unexpected key {key}").format(key=key))

                ret[key] = next(iterator)

            return ret


if TYPE_CHECKING:

    def get_dict_converter(*expected_keys: str, delims: Optional[List[str]] = None) -> Type[dict]:
        ...


else:

    def get_dict_converter(*expected_keys: str, delims: Optional[List[str]] = None) -> Type[dict]:
        """
        Returns a typechecking safe `DictConverter` suitable for use with discord.py
        """

        class PartialMeta(type):
            __call__ = functools.partialmethod(
                type(DictConverter).__call__, *expected_keys, delims=delims
            )

        class ValidatedConverter(DictConverter, metaclass=PartialMeta):
            pass

        return ValidatedConverter


if TYPE_CHECKING:
    TimedeltaConverter = timedelta
else:

    class TimedeltaConverter(dpy_commands.Converter):
        """
        This is a converter for timedeltas.
        The units should be in order from largest to smallest.
        This works with or without whitespace.

        See `parse_timedelta` for more information about how this functions.

        Attributes
        ----------
        maximum : Optional[timedelta]
            If provided, any parsed value higher than this will raise an exception
        minimum : Optional[timedelta]
            If provided, any parsed value lower than this will raise an exception
        allowed_units : Optional[List[str]]
            If provided, you can constrain a user to expressing the amount of time
            in specific units. The units you can choose to provide are the same as the
            parser understands: (``weeks``, ``days``, ``hours``, ``minutes``, ``seconds``)
        default_unit : Optional[str]
            If provided, it will additionally try to match integer-only input into
            a timedelta, using the unit specified. Same units as in ``allowed_units``
            apply.
        """

        def __init__(self, *, minimum=None, maximum=None, allowed_units=None, default_unit=None):
            self.allowed_units = allowed_units
            self.default_unit = default_unit
            self.minimum = minimum
            self.maximum = maximum

        async def convert(self, ctx: "Context", argument: str) -> timedelta:
            if self.default_unit and argument.isdecimal():
                argument = argument + self.default_unit

            delta = parse_timedelta(
                argument,
                minimum=self.minimum,
                maximum=self.maximum,
                allowed_units=self.allowed_units,
            )

            if delta is not None:
                return delta
            raise BadArgument()  # This allows this to be a required argument.


if TYPE_CHECKING:

    def get_timedelta_converter(
        *,
        default_unit: Optional[str] = None,
        maximum: Optional[timedelta] = None,
        minimum: Optional[timedelta] = None,
        allowed_units: Optional[List[str]] = None,
    ) -> Type[timedelta]:
        ...


else:

    def get_timedelta_converter(
        *,
        default_unit: Optional[str] = None,
        maximum: Optional[timedelta] = None,
        minimum: Optional[timedelta] = None,
        allowed_units: Optional[List[str]] = None,
    ) -> Type[timedelta]:
        """
        This creates a type suitable for typechecking which works with discord.py's
        commands.

        See `parse_timedelta` for more information about how this functions.

        Parameters
        ----------
        maximum : Optional[timedelta]
            If provided, any parsed value higher than this will raise an exception
        minimum : Optional[timedelta]
            If provided, any parsed value lower than this will raise an exception
        allowed_units : Optional[List[str]]
            If provided, you can constrain a user to expressing the amount of time
            in specific units. The units you can choose to provide are the same as the
            parser understands: (``weeks``, ``days``, ``hours``, ``minutes``, ``seconds``)
        default_unit : Optional[str]
            If provided, it will additionally try to match integer-only input into
            a timedelta, using the unit specified. Same units as in ``allowed_units``
            apply.

        Returns
        -------
        type
            The converter class, which will be a subclass of `TimedeltaConverter`
        """

        class PartialMeta(type):
            __call__ = functools.partialmethod(
                type(DictConverter).__call__,
                allowed_units=allowed_units,
                default_unit=default_unit,
                minimum=minimum,
                maximum=maximum,
            )

        class ValidatedConverter(TimedeltaConverter, metaclass=PartialMeta):
            pass

        return ValidatedConverter


if not TYPE_CHECKING:

    class NoParseOptional:
        """
        This can be used instead of `typing.Optional`
        to avoid discord.py special casing the conversion behavior.

        .. seealso::
            The `ignore_optional_for_conversion` option of commands.
        """

        def __class_getitem__(cls, key):
            if isinstance(key, tuple):
                raise TypeError("Must only provide a single type to Optional")
            return key


_T = TypeVar("_T")

if not TYPE_CHECKING:
    #: This can be used when user input should be converted as discord.py
    #: treats `typing.Optional`, but the type should not be equivalent to
    #: ``typing.Union[DesiredType, None]`` for type checking.
    #:
    #: Note: In type checking context, this type hint can be passed
    #: multiple types, but such usage is not supported and will fail at runtime
    #:
    #: .. warning::
    #:    This converter class is still provisional.
    UserInputOptional = Optional


if not TYPE_CHECKING:

    class Literal(dpy_commands.Converter):
        """
        This can be used as a converter for `typing.Literal`.

        In a type checking context it is `typing.Literal`.
        In a runtime context, it's a converter which only matches the literals it was given.


        .. warning::
            This converter class is still provisional.
        """

        def __init__(self, valid_names: Tuple[str]):
            self.valid_names = valid_names

        def __call__(self, ctx, arg):
            # Callable's are treated as valid types:
            # https://github.com/python/cpython/blob/3.8/Lib/typing.py#L148
            # Without this, ``typing.Union[Literal["clear"], bool]`` would fail
            return self.convert(ctx, arg)

        async def convert(self, ctx, arg):
            if arg in self.valid_names:
                return arg
            raise BadArgument(_("Expected one of: {}").format(humanize_list(self.valid_names)))

        def __class_getitem__(cls, k):
            if not k:
                raise ValueError("Need at least one value for Literal")
            if isinstance(k, tuple):
                return cls(k)
            else:
                return cls((k,))
