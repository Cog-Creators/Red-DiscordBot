import itertools
from typing import List, Generator

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


def box(text: str, lang: str="") -> str:
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


def bordered(text1: List[str], text2: List[str]) -> str:
    """Get two blocks of text in a borders.

    Note
    ----
    This will only work with a monospaced font.

    Parameters
    ----------
    text1 : `list` of `str`
        The 1st block of text, with each string being a new line.
    text2 : `list` of `str`
        The 2nd block of text. Should not be longer than ``text1``.

    Returns
    -------
    str
        The bordered text.

    """
    width1, width2 = max((len(s1) + 9, len(s2) + 9) for s1 in text1 for s2 in text2)
    res = ['┌{}┐{}┌{}┐'.format("─"*width1, " "*4, "─"*width2)]
    flag = True
    for x, y in itertools.zip_longest(text1, text2):
        if y:
            m = "│{}│{}│{}│".format((x + " " * width1)[:width1], " "*4, (y + " " * width2)[:width2])
        elif x and flag and not y:
            m = "│{}│{}└{}┘".format((x + " " * width1)[:width1], " "*4, "─" *  width2)
            flag = False
        else:
            m = "│{}│".format((x + " " * width1)[:width1])
        res.append(m)
    res.append("└" + "─" * width1 + "┘")
    return "\n".join(res)


def pagify(text: str,
           delims: List[str]=["\n"],
           *,
           priority: bool=False,
           escape_mass_mentions: bool=True,
           shorten_by: int=8,
           page_length: int=2000) -> Generator[str]:
    """Generate multiple pages from the given text.

    Note
    ----
    This does not respect code blocks or inline code.

    Parameters
    ----------
    text : str
        The content to pagify and send.
    delims : `list` of `str`, optional
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
            this_page_len -= (in_text.count("@here", 0, page_length) +
                              in_text.count("@everyone", 0, page_length))
        closest_delim = (in_text.rfind(d, 1, this_page_len)
                         for d in delims)
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


def escape(text: str, *, mass_mentions: bool=False,
           formatting: bool=False) -> str:
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
        text = (text.replace("`", "\\`")
                    .replace("*", "\\*")
                    .replace("_", "\\_")
                    .replace("~", "\\~"))
    return text
