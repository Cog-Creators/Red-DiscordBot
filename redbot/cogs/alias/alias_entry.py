from typing import Tuple

import discord

from redbot.core import commands


class AliasEntry:
    def __init__(
        self, name: str, command: Tuple[str], creator: discord.Member, global_: bool = False
    ):
        super().__init__()
        self.has_real_data = False
        self.name = name
        self.command = command
        self.creator = creator

        self.global_ = global_

        self.guild = None
        if hasattr(creator, "guild"):
            self.guild = creator.guild

        self.uses = 0

    def inc(self):
        """
        Increases the `uses` stat by 1.
        :return: new use count
        """
        self.uses += 1
        return self.uses

    def to_json(self) -> dict:
        try:
            creator = str(self.creator.id)
            guild = str(self.guild.id)
        except AttributeError:
            creator = self.creator
            guild = self.guild

        return {
            "name": self.name,
            "command": self.command,
            "creator": creator,
            "guild": guild,
            "global": self.global_,
            "uses": self.uses,
        }

    @classmethod
    def from_json(cls, data: dict, bot: commands.Bot = None):
        ret = cls(data["name"], data["command"], data["creator"], global_=data["global"])

        if bot:
            ret.has_real_data = True
            ret.creator = bot.get_user(int(data["creator"]))
            guild = bot.get_guild(int(data["guild"]))
            ret.guild = guild
        else:
            ret.guild = data["guild"]

        ret.uses = data.get("uses", 0)
        return ret
