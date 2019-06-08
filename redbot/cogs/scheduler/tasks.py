import dataclasses
import typing

from datetime import datetime, timedelta
from redbot.core.bot import Red

import pytz
import discord


@dataclasses.dataclass()
class ScheduledCommand:
    uuid: str
    command: str
    bot: Red
    author: typing.Union[discord.Member, discord.User]
    channel: typing.Union[discord.TextChannel, discord.User]
    start: datetime
    tz_info: str = "UTC"
    guild_id: typing.Optional[int] = None
    snooze_until: typing.Optional[datetime] = None
    recur: typing.Optional[timedelta] = None 

    def __post_init__(self):
        if self.start.tzinfo is None:
            raise ValueError("Expected start to be timezone aware")
        if self.snooze_until and self.snooze_until.tzinfo is None:
            raise ValueError("Expected snooze_until to be timezone aware")

    def to_config(self):
        return {
            "command": self.command,
            "uuid": self.uuid,
            "user_id": self.author.id,
            "channel_id": self.channel.id,
            "guild_id": self.guild_id,
            "start": self.start.astimezone(pytz.utc).timestamp(),
            "snooze_until": self.snooze_until.astimezone(pytz.utc).timestamp() if self.snooze_until else None,
            "tz_info": self.tz_info,
            "recur": self.recur.total_seconds() if self.recur else None,
        }
    
    @classmethod
    def from_config(cls, bot: Red, **data):
        command = data.pop("command")
        uuid = data.pop("uuid")
        guild_id = data.pop("guild_id", None)
        user_id = data.pop("user_id")
        
        if guild_id:
            guild = bot.get_guild(guild_id)
            channel_id = data.pop("channel_id")
            channel = bot.get_channel(channel_id)
            if channel is None:
                raise ValueError(f"Can't create task for non-existant channel_id: {channel_id}")
            if guild is None:
                raise ValueError(f"Can't create task for non-existant guild_id: {guild_id}")
            author = guild.get_member(data.pop("user_id"))
        else:
            author = channel = bot.get_user(user_id)
        
        if author is None:
            raise ValueError(f"Can't create task for non-existant user_id {user_id}")

        tz_info = data.pop("tz_info", "UTC")
        timezone = pytz.timezone(tz_info)
        start = timezone.fromutc(datetime.fromtimestamp(data.pop("start")))
        snooze_data = data.pop("snooze_until", None)
        snooze_until = None
        if snooze_data is not None:
            snooze_until = timezone.fromutc(datetime.fromtimestamp(snooze_data))

        recur = None
        recur_info = data.pop("recur", None)
        if recur_info is not None:
            recur = timedelta(seconds=recur_info)

        return cls(
            command=command,
            bot=bot,
            guild_id=guild_id,
            author=author,
            channel=channel,
            uuid=uuid,
            tz_info=tz_info,
            snooze_until=snooze_until,
            recur=recur,
            start=start,
        )