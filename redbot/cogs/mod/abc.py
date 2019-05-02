from abc import ABC, abstractmethod
from typing import List, Tuple

import discord
from redbot.core import Config
from redbot.core.bot import Red


class MixinMeta(ABC):
    """
    Base class for well behaved type hint detection with composite class.

    Basically, to keep developers sane when not all attributes are defined in each mixin.
    """

    def __init__(self, *_args):
        self.settings: Config
        self.bot: Red
        self.cache: dict
        self.ban_queue: List[Tuple[int, int]]
        self.unban_queue: List[Tuple[int, int]]
        self._voice_perm_check

    @classmethod
    @abstractmethod
    async def get_audit_entry_info(
        cls, guild: discord.Guild, action: discord.AuditLogAction, target
    ):
        raise NotImplementedError()

    @staticmethod
    @abstractmethod
    async def get_audit_log_entry(guild: discord.Guild, action: discord.AuditLogAction, target):
        raise NotImplementedError()
