import asyncio
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Union, Optional

import discord
from redbot.core.commands import Context
from redbot.core.utils.discord_helpers import OverwriteDiff
from redbot.core.i18n import Translator
from redbot.core.utils.chat_formatting import humanize_timedelta

from .utils import ngettext

ChannelExceptionDict = Dict[discord.abc.GuildChannel, Exception]
ChannelOverwriteDiffDict = Dict[discord.abc.GuildChannel, OverwriteDiff]

_ = Translator("Mutes", __file__)

__all__ = ("ChannelMuteResults", "ServerMuteResults")


@dataclass()
class ChannelMuteResults:
    """ Results of a channel mute """

    target: discord.Member
    expiry: Optional[datetime]
    channel: discord.abc.GuildChannel
    mod: discord.Member
    channel_overwrite_diff: OverwriteDiff

    async def write_config(self, config):
        data = {
            "muted": bool(self.channel_overwrite_diff),
            "target": self.target.id,
            "channel": self.channel.id,
            "expiry": self.expiry.timestamp() if self.expiry else None,
            "perm_diff": self.channel_overwrite_diff.to_dict(),
        }
        await config.custom("CHANNEL_MUTE", self.channel.id, self.target.id).set(data)


@dataclass()
class ServerMuteResults:
    """
    Results of a server mute.
    """

    target: discord.Member
    expiry: Optional[datetime]
    guild: discord.Guild
    mod: discord.Member
    role: Union[discord.Role, None] = None
    channel_diff_map: ChannelOverwriteDiffDict = field(default_factory=ChannelOverwriteDiffDict)
    failure_map: ChannelExceptionDict = field(default_factory=ChannelExceptionDict)

    async def write_config(self, config):
        data = {
            "muted": bool(self.role or self.channel_diff_map),
            "target": self.target.id,
            "expiry": self.expiry.timestamp() if self.expiry else None,
            "role_used": self.role.id if self.role else None,
            "perm_diffs": {
                str(channel.id): diff.to_dict() for channel, diff in self.channel_diff_map.items()
            },
        }
        await config.custom("SERVER_MUTE", self.guild.id, self.target.id).set(data)
