import discord

from cogs.modlog.casetype import Case
from core.bot import Red


class BanCase(Case):
    """Ban case type"""
    @classmethod
    async def from_json(cls, server: discord.Guild,
                        mod_channel: discord.TextChannel,
                        data: dict, bot: Red):
        if data["channel"]:
            channel = server.get_channel(data["channel"])
        else:
            channel = None
        user = bot.get_user(data["user"])
        amended_by = None
        mod = None
        if data["moderator"] is not None:
            mod = server.get_member(data["moderator"])
            if not mod:
                mod = bot.get_user(data["moderator"])
        message = await mod_channel.get_message(data["message"])
        if data["amended_by"] is not None:
            amended_by = server.get_member(data["amended_by"])
            if not amended_by:
                amended_by = bot.get_user(data["amended_by"])

        return cls(server, data["case"], user, data["created_at"],
            modified_at=data["modified_at"], channel=channel,
            reason=data["reason"], moderator=mod, amended_by=amended_by,
            until=data["until"])

    def to_json(self, message: discord.Message):
        out = {
            str(self.case): {
                "case": self.case,
                "created": self.created_at,
                "modified": self.modified_at,
                "action": self.action,
                "user": self.user.id,
                "channel": self.channel.id if self.channel else None,
                "moderator": self.moderator.id if self.moderator else None,
                "amended_by": self.amended_by,
                "message": message.id,
                "until": self.until
            }
        }
        return out

    def __init__(self, **args):
        self.server = args.pop("server", None)
        self.action = BanCase.__name__
        args["action_repr"] = "Ban \N{HAMMER}"
        super().__init__(**args)


class HackbanCase(Case):
    """Hackban case type"""
    @classmethod
    async def from_json(cls, server: discord.Guild,
                        mod_channel: discord.TextChannel,
                        data: dict, bot: Red):
        if data["channel"]:
            channel = server.get_channel(data["channel"])
        else:
            channel = None
        user = bot.get_user(data["user"])
        amended_by = None
        mod = None
        if data["moderator"] is not None:
            mod = server.get_member(data["moderator"])
            if not mod:
                mod = bot.get_user(data["moderator"])
        message = await mod_channel.get_message(data["message"])
        if data["amended_by"] is not None:
            amended_by = server.get_member(data["amended_by"])
            if not amended_by:
                amended_by = bot.get_user(data["amended_by"])

        return cls(server, data["case"], user, data["created_at"],
            modified_at=data["modified_at"], channel=channel, message=message,
            reason=data["reason"], moderator=mod, amended_by=amended_by,
            until=data["until"])

    def to_json(self, message: discord.Message):
        out = {
            str(self.case): {
                "case": self.case,
                "created": self.created_at,
                "modified": self.modified_at,
                "action": self.action,
                "user": self.user.id,
                "channel": self.channel.id if self.channel else None,
                "moderator": self.moderator.id if self.moderator else None,
                "amended_by": self.amended_by,
                "message": message.id,
                "until": self.until
            }
        }
        return out

    def __init__(self, **args):
        self.server = args.pop("server")
        self.action = HackbanCase.__name__
        args["action_repr"] = "Preemptive ban \N{BUST IN SILHOUETTE} \N{HAMMER}"
        super().__init__(**args)


class SoftbanCase(Case):
    """Softban case type"""
    @classmethod
    async def from_json(cls, server: discord.Guild,
                        mod_channel: discord.TextChannel,
                        data: dict, bot: Red):
        if data["channel"]:
            channel = server.get_channel(data["channel"])
        else:
            channel = None
        user = bot.get_user(data["user"])
        amended_by = None
        mod = None
        if data["moderator"] is not None:
            mod = server.get_member(data["moderator"])
            if not mod:
                mod = bot.get_user(data["moderator"])
        message = await mod_channel.get_message(data["message"])
        if data["amended_by"] is not None:
            amended_by = server.get_member(data["amended_by"])
            if not amended_by:
                amended_by = bot.get_user(data["amended_by"])

        return cls(server, data["case"], user, data["created_at"],
            modified_at=data["modified_at"], channel=channel, message=message,
            reason=data["reason"], moderator=mod, amended_by=amended_by,
            until=data["until"])

    def to_json(self, message: discord.Message):
        out = {
            str(self.case): {
                "case": self.case,
                "created": self.created_at,
                "modified": self.modified_at,
                "action": self.action,
                "user": self.user.id,
                "channel": self.channel.id if self.channel else None,
                "moderator": self.moderator.id if self.moderator else None,
                "amended_by": self.amended_by,
                "message": message.id,
                "until": self.until
            }
        }
        return out

    def __init__(self, **args):
        self.server = args.pop("server")
        self.action = SoftbanCase.__name__
        args["action_repr"] = "Softban \N{DASH SYMBOL} \N{HAMMER}"
        super().__init__(**args)


class UnbanCase(Case):
    """Unban case type"""
    @classmethod
    async def from_json(cls, server: discord.Guild,
                        mod_channel: discord.TextChannel,
                        data: dict, bot: Red):
        if data["channel"]:
            channel = server.get_channel(data["channel"])
        else:
            channel = None
        user = bot.get_user(data["user"])
        amended_by = None
        mod = None
        if data["moderator"] is not None:
            mod = server.get_member(data["moderator"])
            if not mod:
                mod = bot.get_user(data["moderator"])
        message = await mod_channel.get_message(data["message"])
        if data["amended_by"] is not None:
            amended_by = server.get_member(data["amended_by"])
            if not amended_by:
                amended_by = bot.get_user(data["amended_by"])

        return cls(server, data["case"], user, data["created_at"],
            modified_at=data["modified_at"], channel=channel, message=message,
            reason=data["reason"], moderator=mod, amended_by=amended_by,
            until=data["until"])

    def to_json(self, message: discord.Message):
        out = {
            str(self.case): {
                "case": self.case,
                "created": self.created_at,
                "modified": self.modified_at,
                "action": self.action,
                "user": self.user.id,
                "channel": self.channel.id if self.channel else None,
                "moderator": self.moderator.id if self.moderator else None,
                "amended_by": self.amended_by,
                "message": message.id,
                "until": self.until
            }
        }
        return out

    def __init__(self, **args):
        self.server = args.pop("server")
        self.action = SoftbanCase.__name__
        args["action_repr"] = "Unban \N{DOVE OF PEACE}"
        super().__init__(**args)


class KickCase(Case):
    """Kick case type"""
    @classmethod
    async def from_json(cls, server: discord.Guild,
                        mod_channel: discord.TextChannel,
                        data: dict, bot: Red):
        if data["channel"]:
            channel = server.get_channel(data["channel"])
        else:
            channel = None
        user = bot.get_user(data["user"])
        amended_by = None
        mod = None
        if data["moderator"] is not None:
            mod = server.get_member(data["moderator"])
            if not mod:
                mod = bot.get_user(data["moderator"])
        message = await mod_channel.get_message(data["message"])
        if data["amended_by"] is not None:
            amended_by = server.get_member(data["amended_by"])
            if not amended_by:
                amended_by = bot.get_user(data["amended_by"])

        return cls(server=server, case=data["case"], user=user, created_at=data["created"],
                   modified_at=data["modified"], channel=channel, message=message,
                   reason=data["reason"], moderator=mod, amended_by=amended_by,
                   until=data["until"])

    def to_json(self, message: discord.Message):
        out = {
            str(self.case): {
                "case": self.case,
                "created": self.created_at,
                "modified": self.modified_at,
                "action": self.action,
                "reason": self.reason,
                "user": self.user.id,
                "channel": self.channel.id if self.channel else None,
                "moderator": self.moderator.id if self.moderator else None,
                "amended_by": self.amended_by,
                "message": message.id,
                "until": self.until
            }
        }
        return out

    def __init__(self, **kwargs):
        self.server = kwargs.pop("server")
        self.action = KickCase.__name__
        kwargs["action_repr"] = "Kick \N{WOMANS BOOTS}"
        super().__init__(**kwargs)


class CMuteCase(Case):
    """Channel mute"""
    @classmethod
    async def from_json(cls, server: discord.Guild,
                        mod_channel: discord.TextChannel,
                        data: dict, bot: Red):
        if data["channel"]:
            channel = server.get_channel(data["channel"])
        else:
            channel = None
        user = bot.get_user(data["user"])
        amended_by = None
        mod = None
        if data["moderator"] is not None:
            mod = server.get_member(data["moderator"])
            if not mod:
                mod = bot.get_user(data["moderator"])
        message = await mod_channel.get_message(data["message"])
        if data["amended_by"] is not None:
            amended_by = server.get_member(data["amended_by"])
            if not amended_by:
                amended_by = bot.get_user(data["amended_by"])

        return cls(server, data["case"], user, data["created_at"],
                   modified_at=data["modified_at"], channel=channel, message=message,
                   reason=data["reason"], moderator=mod, amended_by=amended_by,
                   until=data["until"])

    def to_json(self, message: discord.Message):
        out = {
            str(self.case): {
                "case": self.case,
                "created": self.created_at,
                "modified": self.modified_at,
                "action": self.action,
                "user": self.user.id,
                "channel": self.channel.id if self.channel else None,
                "moderator": self.moderator.id if self.moderator else None,
                "amended_by": self.amended_by,
                "message": message.id,
                "until": self.until
            }
        }
        return out

    def __init__(self, **args):
        self.server = args.pop("server")
        self.action = KickCase.__name__
        args["action_repr"] = "Channel mute \N{SPEAKER WITH CANCELLATION STROKE}"
        super().__init__(**args)


class SMuteCase(Case):
    """Server mute case type"""
    @classmethod
    async def from_json(cls, server: discord.Guild,
                        mod_channel: discord.TextChannel,
                        data: dict, bot: Red):
        if data["channel"]:
            channel = server.get_channel(data["channel"])
        else:
            channel = None
        user = bot.get_user(data["user"])
        amended_by = None
        mod = None
        if data["moderator"] is not None:
            mod = server.get_member(data["moderator"])
            if not mod:
                mod = bot.get_user(data["moderator"])
        message = await mod_channel.get_message(data["message"])
        if data["amended_by"] is not None:
            amended_by = server.get_member(data["amended_by"])
            if not amended_by:
                amended_by = bot.get_user(data["amended_by"])

        return cls(server, data["case"], user, data["created_at"],
            modified_at=data["modified_at"], channel=channel, message=message,
            reason=data["reason"], moderator=mod, amended_by=amended_by,
            until=data["until"])

    def to_json(self, message: discord.Message):
        out = {
            str(self.case): {
                "case": self.case,
                "created": self.created_at,
                "modified": self.modified_at,
                "action": self.action,
                "user": self.user.id,
                "channel": self.channel.id if self.channel else None,
                "moderator": self.moderator.id if self.moderator else None,
                "amended_by": self.amended_by,
                "message": message.id,
                "until": self.until
            }
        }
        return out

    def __init__(self, **args):
        self.server = args.pop("server")
        self.action = KickCase.__name__
        args["action_repr"] = "Server mute \N{SPEAKER WITH CANCELLATION STROKE}"
        super().__init__(**args)
