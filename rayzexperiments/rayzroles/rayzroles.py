"""Core RayzRoles Cog implementation for interactive self-role management."""

import json
from pathlib import Path
from typing import Dict, Optional, Union

import discord
from discord.ext import commands

try:
    from redbot.core import Config, commands as red_commands

    REDBOT_AVAILABLE = True
except ImportError:
    REDBOT_AVAILABLE = False

from .constants import CONFIG_IDENTIFIER, GLOBAL_KEY_MENUS
from .wizard import RoleWizard

FALLBACK_STORE = Path(__file__).parent / "rayzroles_data.json"


class RayzRoles(commands.Cog):
    """Interactive self-role assignment and dynamic role generation cog."""

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if REDBOT_AVAILABLE:
            self.config = Config.get_conf(
                None, identifier=CONFIG_IDENTIFIER, cog_name="RayzRoles", force_registration=True
            )
            default_global = {GLOBAL_KEY_MENUS: {}}
            self.config.register_global(**default_global)
            self._local_cache: Dict[str, Dict[str, int]] = {}
        else:
            self.config = None
            self._local_cache = self._load_fallback_store()

    def _load_fallback_store(self) -> Dict[str, Dict[str, int]]:
        if FALLBACK_STORE.exists():
            try:
                with open(FALLBACK_STORE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_fallback_store(self) -> None:
        try:
            with open(FALLBACK_STORE, "w", encoding="utf-8") as f:
                json.dump(self._local_cache, f, indent=2)
        except Exception as exc:
            print(f"[RayzRoles] Error saving local store: {exc}")

    async def _get_menus(self) -> Dict[str, Dict[str, int]]:
        if self.config:
            return await self.config.get_raw(GLOBAL_KEY_MENUS, default={})
        return self._local_cache

    async def _save_menu(self, message_id: str, mappings: Dict[str, int]) -> None:
        if self.config:
            async with self.config.all() as data:
                menus = data.setdefault(GLOBAL_KEY_MENUS, {})
                menus[message_id] = mappings
        else:
            self._local_cache[message_id] = mappings
            self._save_fallback_store()

    @commands.guild_only()
    @commands.has_permissions(manage_roles=True)
    @commands.bot_has_permissions(manage_roles=True, add_reactions=True, embed_links=True)
    @commands.command(name="re")
    async def re_wizard(
        self,
        ctx: commands.Context,
        target_channel: Optional[Union[discord.TextChannel, discord.Thread]] = None,
    ) -> None:
        """Starts an interactive wizard to configure self-assignable roles.

        Usage:
            re #channel-name
            re 123456789012345678
            re
        """
        destination = target_channel or ctx.channel
        wizard = RoleWizard(self.bot, ctx, destination)
        results = await wizard.run()

        if not results:
            return

        embed = RoleWizard.build_menu_embed(results)
        try:
            target_message = await destination.send(embed=embed)
            for emoji_str, _ in results:
                await target_message.add_reaction(emoji_str)
        except discord.Forbidden:
            await ctx.send(
                f"Missing permissions to write or add reactions in {destination.mention}."
            )
            return

        stored_map = {emoji: role.id for emoji, role in results}
        await self._save_menu(str(target_message.id), stored_map)

        await ctx.send(
            f"Self-role menu successfully deployed to {destination.mention} with {len(results)} roles."
        )

    @commands.Cog.listener()
    async def on_raw_reaction_add(self, payload: discord.RawReactionActionEvent) -> None:
        """Assigns the role when a user reacts on an active role menu."""
        if not payload.guild_id or (self.bot.user and payload.user_id == self.bot.user.id):
            return

        menus = await self._get_menus()
        msg_id_str = str(payload.message_id)
        if msg_id_str not in menus:
            return

        role_map = menus[msg_id_str]
        emoji_key = str(payload.emoji)
        role_id = role_map.get(emoji_key) or role_map.get(payload.emoji.name)
        if not role_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        role = guild.get_role(role_id)
        member = payload.member or guild.get_member(payload.user_id)
        if not role or not member:
            return

        if role >= guild.me.top_role:
            return

        try:
            await member.add_roles(role, reason="RayzRoles: self-role reaction added")
            try:
                await member.send(f"Added role '{role.name}' in '{guild.name}'.")
            except discord.Forbidden:
                pass
        except discord.Forbidden:
            pass

    @commands.Cog.listener()
    async def on_raw_reaction_remove(self, payload: discord.RawReactionActionEvent) -> None:
        """Removes the role when a user unreacts on an active role menu."""
        if not payload.guild_id or (self.bot.user and payload.user_id == self.bot.user.id):
            return

        menus = await self._get_menus()
        msg_id_str = str(payload.message_id)
        if msg_id_str not in menus:
            return

        role_map = menus[msg_id_str]
        emoji_key = str(payload.emoji)
        role_id = role_map.get(emoji_key) or role_map.get(payload.emoji.name)
        if not role_id:
            return

        guild = self.bot.get_guild(payload.guild_id)
        if not guild:
            return

        role = guild.get_role(role_id)
        member = guild.get_member(payload.user_id)
        if not role or not member:
            return

        if role >= guild.me.top_role:
            return

        try:
            await member.remove_roles(role, reason="RayzRoles: self-role reaction removed")
            try:
                await member.send(f"Removed role '{role.name}' in '{guild.name}'.")
            except discord.Forbidden:
                pass
        except discord.Forbidden:
            pass
