from datetime import datetime

import discord

from core.bot import Red
from cogs.mod.common import strfdelta
from core.utils.chat_formatting import bold


class Case:
    """Base class for modlog cases
    This should never be instantiated directly;
    instead, it should be subclassed"""

    def __init__(self, **kwargs):
        self.case = kwargs.pop("case")
        self.created_at = kwargs.pop("created_at")
        self.modified_at = kwargs.pop("modified_at", None)
        self.channel = kwargs.pop("channel")
        self.reason = kwargs.pop("reason", None)
        self.user = kwargs.pop("user")
        self.action_repr = kwargs.pop("action_repr")
        self.moderator = kwargs.pop("moderator", None)
        self.amended_by = kwargs.pop("amended_by", None)
        self.message = kwargs.pop("message", None)
        self.until = kwargs.pop("until", None)

    def __str__(self):
        """Replacement for 'format_case_msg'"""
        case_type = ""
        case_type += "{} | {}\n".format(bold("Case #{}".format(self.case)), self.action_repr)
        case_type += "**User:** {}#{} ({})\n".format(self.user.name, self.user.discriminator, self.user.id)
        if self.moderator:
            case_type += "**Moderator:** {}#{} ({})\n".format(
                self.moderator.name, self.moderator.discriminator, self.moderator.id
            )
        else:
            case_type += "**Moderator:** Unknown (Nobody has claimed responsibility yet)"
        if self.created_at and self.until:
            start = datetime.fromtimestamp(self.created_at)
            end = datetime.fromtimestamp(self.until)
            end_fmt = end.strftime('%Y-%m-%d %H:%M:%S UTC')
            duration = end - start
            dur_fmt = strfdelta(duration)
            case_type += ("**Until:** {}\n"
                          "**Duration:** {}\n").format(end_fmt, dur_fmt)
        if self.amended_by:
            case_type += "**Amended by:** {}#{} ({})\n".format(
                self.amended_by.name, self.amended_by.discriminator, self.amended_by.id)
        if self.modified_at:
            case_type += "**Last modified**: {}\n".format(
                datetime.fromtimestamp(
                    self.modified_at
                ).strftime('%Y-%m-%d %H:%M:%S UTC')
            )
        if self.reason:
            case_type += "**Reason:** {}".format(self.reason)
        else:
            case_type += "**Reason:** Type [p]reason {} <reason> to add it".format(self.case)
        return case_type

    def to_json(self, message: discord.Message):
        raise NotImplementedError

    @classmethod
    async def from_json(cls, server: discord.Guild,
                        mod_channel: discord.TextChannel,
                        data: dict, bot: Red):
        raise NotImplementedError
