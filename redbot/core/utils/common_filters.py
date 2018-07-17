import re

__all__ = ["filter_urls", "filter_invites", "filter_mass_mentions"]

# regexes
URL_RE = re.compile(r"(https?|s?ftp)://(\S+)", re.I)

INVITE_URL_RE = re.compile(r"(discord.gg|discordapp.com/invite|discord.me)(\S+)", re.I)

MASS_MENTION_RE = re.compile(r"(@)(?=everyone|here)")  # This only matches the @ for sanitizing


# convienience wrappers
def filter_urls(to_filter: str) -> str:
    return URL_RE.sub("[SANITIZED URL]", to_filter)


def filter_invites(to_filter: str) -> str:
    return INVITE_URL_RE.sub("[SANITIZED INVITE]", to_filter)


def filter_mass_mentions(to_filter: str) -> str:
    return MASS_MENTION_RE.sub("@\u200b", to_filter)
