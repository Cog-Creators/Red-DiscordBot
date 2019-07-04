import itertools
import datetime
from typing import Sequence, Iterator, List, Optional, Union

import discord
from babel.numbers import format_decimal

from redbot.core.i18n import Translator, get_locale

_ = Translator("UtilsChatFormatting", __file__)


def error(text: str) -> str:
    """Get text prefixed with an error emoji.

    Returns
    -------
    str
        The new message.

    """
    return "\N{NO ENTRY SIGN} {}".format(text)


def warning(text: str) -> str:
    """Get text prefixed with a warning emoji.

    Returns
    -------
    str
        The new message.

    """
    return "\N{WARNING SIGN} {}".format(text)


def info(text: str) -> str:
    """Get text prefixed with an info emoji.

    Returns
    -------
    str
        The new message.

    """
    return "\N{INFORMATION SOURCE} {}".format(text)


def question(text: str) -> str:
    """Get text prefixed with a question emoji.

    Returns
    -------
    str
        The new message.

    """
    return "\N{BLACK QUESTION MARK ORNAMENT} {}".format(text)


def bold(text: str) -> str:
    """Get the given text in bold.

    Parameters
    ----------
    text : str
        The text to be marked up.

    Returns
    -------
    str
        The marked up text.

    """
    text = escape(text, formatting=True)
    return "**{}**".format(text)


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
    ret = "```{}\n{}\n```".format(lang, text)
    return ret


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
        return "``{}``".format(text)
    else:
        return "`{}`".format(text)


def italics(text: str) -> str:
    """Get the given text in italics.

    Parameters
    ----------
    text : str
        The text to be marked up.

    Returns
    -------
    str
        The marked up text.

    """
    text = escape(text, formatting=True)
    return "*{}*".format(text)


def bordered(*columns: Sequence[str], ascii_border: bool = False) -> str:
    """Get two blocks of text in a borders.

    Note
    ----
    This will only work with a monospaced font.

    Parameters
    ----------
    *columns : `sequence` of `str`
        The columns of text, each being a list of lines in that column.
    ascii_border : bool
        Whether or not the border should be pure ASCII.

    Returns
    -------
    str
        The bordered text.

    """
    borders = {
        "TL": "-" if ascii_border else "┌",  # Top-left
        "TR": "-" if ascii_border else "┐",  # Top-right
        "BL": "-" if ascii_border else "└",  # Bottom-left
        "BR": "-" if ascii_border else "┘",  # Bottom-right
        "HZ": "-" if ascii_border else "─",  # Horizontal
        "VT": "|" if ascii_border else "│",  # Vertical
    }

    sep = " " * 4  # Separator between boxes
    widths = tuple(max(len(row) for row in column) + 9 for column in columns)  # width of each col
    colsdone = [False] * len(columns)  # whether or not each column is done
    lines = [sep.join("{TL}" + "{HZ}" * width + "{TR}" for width in widths)]

    for line in itertools.zip_longest(*columns):
        row = []
        for colidx, column in enumerate(line):
            width = widths[colidx]
            done = colsdone[colidx]
            if column is None:
                if not done:
                    # bottom border of column
                    column = "{HZ}" * width
                    row.append("{BL}" + column + "{BR}")
                    colsdone[colidx] = True  # mark column as done
                else:
                    # leave empty
                    row.append(" " * (width + 2))
            else:
                column += " " * (width - len(column))  # append padded spaces
                row.append("{VT}" + column + "{VT}")

        lines.append(sep.join(row))

    final_row = []
    for width, done in zip(widths, colsdone):
        if not done:
            final_row.append("{BL}" + "{HZ}" * width + "{BR}")
        else:
            final_row.append(" " * (width + 2))
    lines.append(sep.join(final_row))

    return "\n".join(lines).format(**borders)


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


def strikethrough(text: str) -> str:
    """Get the given text with a strikethrough.

    Parameters
    ----------
    text : str
        The text to be marked up.

    Returns
    -------
    str
        The marked up text.

    """
    text = escape(text, formatting=True)
    return "~~{}~~".format(text)


def underline(text: str) -> str:
    """Get the given text with an underline.

    Parameters
    ----------
    text : str
        The text to be marked up.

    Returns
    -------
    str
        The marked up text.

    """
    text = escape(text, formatting=True)
    return "__{}__".format(text)


def escape(text: str, *, mass_mentions: bool = False, formatting: bool = False) -> str:
    """Get text with all mass mentions or markdown escaped.

    Parameters
    ----------
    text : str
        The text to be escaped.
    mass_mentions : `bool`, optional
        Set to :code:`True` to escape mass mentions in the text.
    formatting : `bool`, optional
        Set to :code:`True` to escpae any markdown formatting in the text.

    Returns
    -------
    str
        The escaped text.

    """
    if mass_mentions:
        text = text.replace("@everyone", "@\u200beveryone")
        text = text.replace("@here", "@\u200bhere")
    if formatting:
        text = text.replace("`", "\\`").replace("*", "\\*").replace("_", "\\_").replace("~", "\\~")
    return text


def humanize_list(items: Sequence[str]) -> str:
    """Get comma-separted list, with the last element joined with *and*.

    This uses an Oxford comma, because without one, items containing
    the word *and* would make the output difficult to interpret.

    Parameters
    ----------
    items : Sequence[str]
        The items of the list to join together.

    Raises
    ------
    IndexError
        An empty sequence was passed

    Examples
    --------
    .. testsetup::

        from redbot.core.utils.chat_formatting import humanize_list

    .. doctest::

        >>> humanize_list(['One', 'Two', 'Three'])
        'One, Two, and Three'
        >>> humanize_list(['One'])
        'One'

    """
    if len(items) == 1:
        return items[0]
    try:
        return ", ".join(items[:-1]) + _(", and ") + items[-1]
    except IndexError:
        raise IndexError("Cannot humanize empty sequence") from None


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
    *, timedelta: Optional[datetime.timedelta] = None, seconds: Optional[int] = None
) -> str:
    """
    Get a human timedelta representation
    """

    try:
        obj = seconds or timedelta.total_seconds()
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


def humanize_int(val: Union[int, float]) -> str:
    """
    Convert an int to a str with digit separators based on bot locale

    Parameters
    ----------
    val : Union[int, float]
        The int to be formatted.

    Returns
    -------
    str
        locale aware formated number.
    """
    return format_decimal(val, locale=get_locale())
