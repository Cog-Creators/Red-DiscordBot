def error(text):
    return "\N{NO ENTRY SIGN} {}".format(text)


def warning(text):
    return "\N{WARNING SIGN} {}".format(text)


def info(text):
    return "\N{INFORMATION SOURCE} {}".format(text)


def question(text):
    return "\N{BLACK QUESTION MARK ORNAMENT} {}".format(text)


def bold(text):
    return "**{}**".format(text)


def box(text, lang=""):
    ret = "```{}\n{}\n```".format(lang, text)
    return ret


def inline(text):
    return "`{}`".format(text)


def italics(text):
    return "*{}*".format(text)


def pagify(text, delims=["\n"], *, escape_mass_mentions=True, shorten_by=8,
           page_length=2000):
    """DOES NOT RESPECT MARKDOWN BOXES OR INLINE CODE"""
    in_text = text
    page_length -= shorten_by
    while len(in_text) > page_length:
        this_page_len = page_length
        if escape_mass_mentions:
            this_page_len -= (in_text.count("@here", 0, page_length) +
                              in_text.count("@everyone", 0, page_length))
        closest_delim = max([in_text.rfind(d, 1, this_page_len)
                             for d in delims])
        closest_delim = closest_delim if closest_delim != -1 else this_page_length
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


def strikethrough(text):
    return "~~{}~~".format(text)


def underline(text):
    return "__{}__".format(text)


def escape(text, *, mass_mentions=False, formatting=False):
    if mass_mentions:
        text = text.replace("@everyone", "@\u200beveryone")
        text = text.replace("@here", "@\u200bhere")
    if formatting:
        text = (text.replace("`", "\\`")
                    .replace("*", "\\*")
                    .replace("_", "\\_")
                    .replace("~", "\\~"))
    return text
