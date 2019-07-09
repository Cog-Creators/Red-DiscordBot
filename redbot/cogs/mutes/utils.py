import discord
from redbot.core.i18n import Translator

from .errors import PermError

_ = Translator("Mutes", __file__)


def ngettext(singular: str, plural: str, count: int, **fmt_kwargs) -> str:
    """
    This isn't a full ngettext
    Replace this with babel when Red can use that.
    """
    return singular.format(**fmt_kwargs) if count == 1 else plural.format(**fmt_kwargs)


def hierarchy_check(*, mod: discord.Member, target: discord.Member):
    """
    Checks that things are hierarchy safe

    This does not check the bot can modify permissions.
    This is assumed to be checked prior to command invocation.
    
    Parameters
    -----------
    mod : discord.Member
        The responsible moderator
    target : discord.Member
        The target of a mute

    Raises
    ------
    PermError
        Any of:
            - The target is above either the mod or bot.
            - The target had the administrator perm
            - The target is the guild owner
        This error will contain a user facing error message.
    """
    if target == target.guild.owner:
        raise PermError(friendly_error=_("You can't mute the owner of a guild."))

    if target.guild_permissions.administrator:
        raise PermError(
            friendly_error=_("You can't mute someone with the administrator permission.")
        )

    if target.top_role >= target.guild.me:
        raise PermError(friendly_error=_("I can't mute this user. (Discord Hierarchy applies)"))

    if target.top_role >= mod.top_role:
        raise PermError(friendly_error=_("You can't mute this user. (Discord Hierarchy applies)"))
