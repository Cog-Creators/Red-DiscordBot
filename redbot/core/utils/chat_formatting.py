import itertools
from typing import Sequence, Iterator, List
from redbot.core.i18n import Translator

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
    page_length: int = 2000
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


def humanize_list(words: List[str]):
    """Get comma-separted list, with the last element joined with *and*.

    Examples
    --------
    .. doctest::

        >>>humanized_list(["One", "Two", "Three"])
        "One, Two and Three"

    .. doctest::

        >>>humanized_list(["One"])
        "One"

    """
    if len(words) == 1:
        return words[0]
    return ", ".join(words[:-1]) + _(" and ") + words[-1]
