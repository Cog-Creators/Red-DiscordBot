import datetime
import itertools
import textwrap
from io import BytesIO
from typing import Iterator, List, Optional, Sequence, SupportsInt, Union

import discord
from babel.lists import format_list as babel_list
from babel.numbers import format_decimal

from redbot.core.i18n import Translator, get_babel_locale, get_babel_regional_format

_ = Translator("UtilsChatFormatting", __file__)


def error(text: str) -> str:
    """Get text prefixed with an error emoji.

    Parameters
    ----------
    text : str
        The text to be prefixed.

    Returns
    -------
    str
        The new message.

    """
    return f"\N{NO ENTRY SIGN} {text}"


def warning(text: str) -> str:
    """Get text prefixed with a warning emoji.

    Parameters
    ----------
    text : str
        The text to be prefixed.

    Returns
    -------
    str
        The new message.

    """
    return f"\N{WARNING SIGN}\N{VARIATION SELECTOR-16} {text}"


def info(text: str) -> str:
    """Get text prefixed with an info emoji.

    Parameters
    ----------
    text : str
        The text to be prefixed.

    Returns
    -------
    str
        The new message.

    """
    return f"\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16} {text}"


def success(text: str) -> str:
    """Get text prefixed with a success emoji.

    Parameters
    ----------
    text : str
        The text to be prefixed.

    Returns
    -------
    str
        The new message.

    """
    return f"\N{WHITE HEAVY CHECK MARK} {text}"


def question(text: str) -> str:
    """Get text prefixed with a question emoji.

    Parameters
    ----------
    text : str
        The text to be prefixed.

    Returns
    -------
    str
        The new message.

    """
    return f"\N{BLACK QUESTION MARK ORNAMENT}\N{VARIATION SELECTOR-16} {text}"


def bold(text: str, escape_formatting: bool = True) -> str:
    """Get the given text in bold.

    Note: By default, this function will escape ``text`` prior to emboldening.

    Parameters
    ----------
    text : str
        The text to be marked up.
    escape_formatting : `bool`, optional
        Set to :code:`False` to not escape markdown formatting in the text.

    Returns
    -------
    str
        The marked up text.

    """
    return f"**{escape(text, formatting=escape_formatting)}**"


def box(text: str, lang: str = "") -> str:
    """Get the given text in a code block.

    Parameters
    ----------
    text : str
        The text to be marked up.
    lang : `str`, optional
        The syntax highlighting language for the codeblock.

    Returns
    -------
    str
        The marked up text.

    """
    return f"```{lang}\n{text}\n```"


def inline(text: str) -> str:
    """Get the given text as inline code.

    Parameters
    ----------
    text : str
        The text to be marked up.

    Returns
    -------
    str
        The marked up text.

    """
    if "`" in text:
        return f"``{text}``"
    else:
        return f"`{text}`"


def italics(text: str, escape_formatting: bool = True) -> str:
    """Get the given text in italics.

    Note: By default, this function will escape ``text`` prior to italicising.

    Parameters
    ----------
    text : str
        The text to be marked up.
    escape_formatting : `bool`, optional
        Set to :code:`False` to not escape markdown formatting in the text.

    Returns
    -------
    str
        The marked up text.

    """
    return f"*{escape(text, formatting=escape_formatting)}*"


def spoiler(text: str, escape_formatting: bool = True) -> str:
    """Get the given text as a spoiler.

    Note: By default, this function will escape ``text`` prior to making the text a spoiler.

    Parameters
    ----------
    text : str
        The text to be marked up.
    escape_formatting : `bool`, optional
        Set to :code:`False` to not escape markdown formatting in the text.

    Returns
    -------
    str
        The marked up text.

    """
    return f"||{escape(text, formatting=escape_formatting)}||"


def pagify(
    text: str,
    delims: Sequence[str] = ["\n"],
    *,
    priority: bool = False,
    escape_mass_mentions: bool = True,
    shorten_by: int = 8,
    page_length: int = 2000,
) -> Iterator[str]:
    """Generate multiple pages from the given text.

    Note
    ----
    This does not respect code blocks or inline code.

    Parameters
    ----------
    text : str
        The content to pagify and send.
    delims : `sequence` of `str`, optional
        Characters where page breaks will occur. If no delimiters are found
        in a page, the page will break after ``page_length`` characters.
        By default this only contains the newline.

    Other Parameters
    ----------------
    priority : `bool`
        Set to :code:`True` to choose the page break delimiter based on the
        order of ``delims``. Otherwise, the page will always break at the
        last possible delimiter.
    escape_mass_mentions : `bool`
        If :code:`True`, any mass mentions (here or everyone) will be
        silenced.
    shorten_by : `int`
        How much to shorten each page by. Defaults to 8.
    page_length : `int`
        The maximum length of each page. Defaults to 2000.

    Yields
    ------
    `str`
        Pages of the given text.

    """
    in_text = text
    page_length -= shorten_by
    while len(in_text) > page_length:
        this_page_len = page_length
        if escape_mass_mentions:
            this_page_len -= in_text.count("@here", 0, page_length) + in_text.count(
                "@everyone", 0, page_length
            )
        closest_delim = (in_text.rfind(d, 1, this_page_len) for d in delims)
        if priority:
            closest_delim = next((x for x in closest_delim if x > 0), -1)
        else:
            closest_delim = max(closest_delim)
        closest_delim = closest_delim if closest_delim != -1 else this_page_len
        if escape_mass_mentions:
            to_send = escape(in_text[:closest_delim], mass_mentions=True)
        else:
            to_send = in_text[:closest_delim]
        if len(to_send.strip()) > 0:
            yield to_send
        in_text = in_text[closest_delim:]

    if len(in_text.strip()) > 0:
        if escape_mass_mentions:
            yield escape(in_text, mass_mentions=True)
        else:
            yield in_text


def strikethrough(text: str, escape_formatting: bool = True) -> str:
    """Get the given text with a strikethrough.

    Note: By default, this function will escape ``text`` prior to applying a strikethrough.

    Parameters
    ----------
    text : str
        The text to be marked up.
    escape_formatting : `bool`, optional
        Set to :code:`False` to not escape markdown formatting in the text.

    Returns
    -------
    str
        The marked up text.

    """
    return f"~~{escape(text, formatting=escape_formatting)}~~"


def underline(text: str, escape_formatting: bool = True) -> str:
    """Get the given text with an underline.

    Note: By default, this function will escape ``text`` prior to underlining.

    Parameters
    ----------
    text : str
        The text to be marked up.
    escape_formatting : `bool`, optional
        Set to :code:`False` to not escape markdown formatting in the text.

    Returns
    -------
    str
        The marked up text.

    """
    return f"__{escape(text, formatting=escape_formatting)}__"


def quote(text: str) -> str:
    """Quotes the given text.

    Parameters
    ----------
    text : str
        The text to be marked up.

    Returns
    -------
    str
        The marked up text.

    """
    return textwrap.indent(text, "> ", lambda l: True)


def escape(text: str, *, mass_mentions: bool = False, formatting: bool = False) -> str:
    """Get text with all mass mentions or markdown escaped.

    Parameters
    ----------
    text : str
        The text to be escaped.
    mass_mentions : `bool`, optional
        Set to :code:`True` to escape mass mentions in the text.
    formatting : `bool`, optional
        Set to :code:`True` to escape any markdown formatting in the text.

    Returns
    -------
    str
        The escaped text.

    """
    if mass_mentions:
        text = text.replace("@everyone", "@\u200beveryone")
        text = text.replace("@here", "@\u200bhere")
    if formatting:
        text = discord.utils.escape_markdown(text)
    return text


def humanize_list(
    items: Sequence[str], *, locale: Optional[str] = None, style: str = "standard"
) -> str:
    """Get comma-separated list, with the last element joined with *and*.

    Parameters
    ----------
    items : Sequence[str]
        The items of the list to join together.
    locale : Optional[str]
        The locale to convert, if not specified it defaults to the bot's locale.
    style : str
        The style to format the list with.

        Note: Not all styles are necessarily available in all locales,
        see documentation of `babel.lists.format_list` for more details.

        standard
            A typical 'and' list for arbitrary placeholders.
            eg. "January, February, and March"
        standard-short
             A short version of a 'and' list, suitable for use with short or
             abbreviated placeholder values.
             eg. "Jan., Feb., and Mar."
        or
            A typical 'or' list for arbitrary placeholders.
            eg. "January, February, or March"
        or-short
            A short version of an 'or' list.
            eg. "Jan., Feb., or Mar."
        unit
            A list suitable for wide units.
            eg. "3 feet, 7 inches"
        unit-short
            A list suitable for short units
            eg. "3 ft, 7 in"
        unit-narrow
            A list suitable for narrow units, where space on the screen is very limited.
            eg. "3′ 7″"

    Raises
    ------
    ValueError
        The locale does not support the specified style.

    Examples
    --------
    .. testsetup::

        from redbot.core.utils.chat_formatting import humanize_list

    .. doctest::

        >>> humanize_list(['One', 'Two', 'Three'])
        'One, Two, and Three'
        >>> humanize_list(['One'])
        'One'
        >>> humanize_list(['omena', 'peruna', 'aplari'], style='or', locale='fi')
        'omena, peruna tai aplari'

    """

    return babel_list(items, style=style, locale=get_babel_locale(locale))


def format_perms_list(perms: discord.Permissions) -> str:
    """Format a list of permission names.

    This will return a humanized list of the names of all enabled
    permissions in the provided `discord.Permissions` object.

    Parameters
    ----------
    perms : discord.Permissions
        The permissions object with the requested permissions to list
        enabled.

    Returns
    -------
    str
        The humanized list.

    """
    perm_names: List[str] = []
    for perm, value in perms:
        if value is True:
            perm_name = '"' + perm.replace("_", " ").title() + '"'
            perm_names.append(perm_name)
    return humanize_list(perm_names).replace("Guild", "Server")


def humanize_timedelta(
    *, timedelta: Optional[datetime.timedelta] = None, seconds: Optional[SupportsInt] = None
) -> str:
    """
    Get a locale aware human timedelta representation.

    This works with either a timedelta object or a number of seconds.

    Fractional values will be omitted, and values less than 1 second
    an empty string.

    Parameters
    ----------
    timedelta: Optional[datetime.timedelta]
        A timedelta object
    seconds: Optional[SupportsInt]
        A number of seconds

    Returns
    -------
    str
        A locale aware representation of the timedelta or seconds.

    Raises
    ------
    ValueError
        The function was called with neither a number of seconds nor a timedelta object
    """

    try:
        obj = seconds if seconds is not None else timedelta.total_seconds()
    except AttributeError:
        raise ValueError("You must provide either a timedelta or a number of seconds")

    seconds = int(obj)
    periods = [
        (_("year"), _("years"), 60 * 60 * 24 * 365),
        (_("month"), _("months"), 60 * 60 * 24 * 30),
        (_("day"), _("days"), 60 * 60 * 24),
        (_("hour"), _("hours"), 60 * 60),
        (_("minute"), _("minutes"), 60),
        (_("second"), _("seconds"), 1),
    ]

    strings = []
    for period_name, plural_period_name, period_seconds in periods:
        if seconds >= period_seconds:
            period_value, seconds = divmod(seconds, period_seconds)
            if period_value == 0:
                continue
            unit = plural_period_name if period_value > 1 else period_name
            strings.append(f"{period_value} {unit}")

    return ", ".join(strings)


def humanize_number(val: Union[int, float], override_locale=None) -> str:
    """
    Convert an int or float to a str with digit separators based on bot locale

    Parameters
    ----------
    val : Union[int, float]
        The int/float to be formatted.
    override_locale: Optional[str]
        A value to override bot's regional format.

    Returns
    -------
    str
        locale aware formatted number.
    """
    return format_decimal(val, locale=get_babel_regional_format(override_locale))


def text_to_file(
    text: str, filename: str = "file.txt", *, spoiler: bool = False, encoding: str = "utf-8"
):
    """Prepares text to be sent as a file on Discord, without character limit.

    This writes text into a bytes object that can be used for the ``file`` or ``files`` parameters
    of :meth:`discord.abc.Messageable.send`.

    Parameters
    ----------
    text: str
        The text to put in your file.
    filename: str
        The name of the file sent. Defaults to ``file.txt``.
    spoiler: bool
        Whether the attachment is a spoiler. Defaults to ``False``.

    Returns
    -------
    discord.File
        The file containing your text.

    """
    file = BytesIO(text.encode(encoding))
    return discord.File(file, filename, spoiler=spoiler)
