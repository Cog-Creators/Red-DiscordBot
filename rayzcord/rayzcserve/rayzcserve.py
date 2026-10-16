"""Main RayzCServe Cog implementation for Discord server typography automation."""

import json
from pathlib import Path
from typing import Dict, Optional

import discord
from discord.ext import commands

try:
    from redbot.core import Config, commands as red_commands

    REDBOT_AVAILABLE = True
except ImportError:
    REDBOT_AVAILABLE = False

from .applier import ServerStyleApplier
from .constants import (
    CONFIG_IDENTIFIER,
    FONTS_PER_PAGE,
    GLOBAL_KEY_SNAPSHOTS,
    PROMPT_UNDO_NONE,
    PROMPT_UNDO_SUCCESS,
)
from .fonts import FONTS, format_font_page, get_font
from .symbols import get_symbol
from .wizard import ServerStyleWizard

FALLBACK_SNAPSHOT_STORE = Path(__file__).parent / "rayzcserve_snapshots.json"


class RayzCServe(commands.Cog):
    """Server-wide typography and aesthetic font customization cog.

    Created by Ray (rayzien).
    Allows selecting from 100+ fonts and aesthetic symbol presets,
    and batch-applying styling to server channels, categories, and roles.
    """

    def __init__(self, bot: commands.Bot):
        self.bot = bot
        if REDBOT_AVAILABLE:
            self.config = Config.get_conf(
                None, identifier=CONFIG_IDENTIFIER, cog_name="RayzCServe", force_registration=True
            )
            default_guild = {GLOBAL_KEY_SNAPSHOTS: {}}
            self.config.register_guild(**default_guild)
            self._local_snapshots: Dict[str, Dict[str, Dict[str, str]]] = {}
        else:
            self.config = None
            self._local_snapshots = self._load_fallback_snapshots()

    def _load_fallback_snapshots(self) -> Dict[str, Dict[str, Dict[str, str]]]:
        if FALLBACK_SNAPSHOT_STORE.exists():
            try:
                with open(FALLBACK_SNAPSHOT_STORE, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def _save_fallback_snapshots(self) -> None:
        try:
            with open(FALLBACK_SNAPSHOT_STORE, "w", encoding="utf-8") as f:
                json.dump(self._local_snapshots, f, indent=2)
        except Exception as exc:
            print(f"[RayzCServe] Error saving snapshot store: {exc}")

    async def _save_snapshot(self, guild_id: int, snapshot: Dict[str, Dict[str, str]]) -> None:
        if self.config:
            await self.config.guild_from_id(guild_id).snapshots.set(snapshot)
        else:
            self._local_snapshots[str(guild_id)] = snapshot
            self._save_fallback_snapshots()

    async def _get_snapshot(self, guild_id: int) -> Optional[Dict[str, Dict[str, str]]]:
        if self.config:
            return await self.config.guild_from_id(guild_id).snapshots()
        return self._local_snapshots.get(str(guild_id))

    @commands.guild_only()
    @commands.has_permissions(manage_guild=True, manage_channels=True, manage_roles=True)
    @commands.bot_has_permissions(manage_channels=True, manage_roles=True)
    @commands.group(name="rcs", invoke_without_command=True)
    async def rcs_group(self, ctx: commands.Context) -> None:
        """Launches the interactive server-wide typography wizard."""
        wizard = ServerStyleWizard(self.bot, ctx)
        result = await wizard.run()
        if result and "snapshot" in result:
            await self._save_snapshot(ctx.guild.id, result["snapshot"])

    @rcs_group.command(name="undo")
    async def rcs_undo(self, ctx: commands.Context) -> None:
        """Restores server element names from the last recorded backup snapshot."""
        snapshot = await self._get_snapshot(ctx.guild.id)
        if not snapshot or (not snapshot.get("channels") and not snapshot.get("roles")):
            await ctx.send(PROMPT_UNDO_NONE)
            return

        status_msg = await ctx.send("Restoring original server element names from snapshot...")
        reverted_ch, reverted_roles = await ServerStyleApplier.revert_snapshot(ctx.guild, snapshot)
        await status_msg.edit(
            content=f"{PROMPT_UNDO_SUCCESS} Reverted {reverted_ch} channels and {reverted_roles} roles."
        )

    @rcs_group.command(name="fonts")
    async def rcs_fonts(self, ctx: commands.Context, page: int = 1) -> None:
        """Displays available typography styles page by page (1-11)."""
        sample = ctx.channel.name if ctx.channel else "general"
        page_text = format_font_page(page, FONTS_PER_PAGE, sample_text=sample)
        embed = discord.Embed(
            title="Available Typography Styles",
            description=f"```\n{page_text}\n```",
            colour=discord.Colour.dark_teal(),
        )
        embed.set_footer(
            text=f"Use 'rcs fonts <page>' to view other pages (1-11). Total fonts: {len(FONTS)}."
        )
        await ctx.send(embed=embed)

    @rcs_group.command(name="preview")
    async def rcs_preview(
        self,
        ctx: commands.Context,
        font_id: int,
        symbol_id: Optional[int] = None,
        *,
        sample_text: str = "announcements",
    ) -> None:
        """Previews a font and optional symbol pattern on custom text."""
        font_obj = get_font(font_id)
        if not font_obj:
            await ctx.send(f"Invalid font ID {font_id}. Choose between 1 and {len(FONTS)}.")
            return

        styled = font_obj.transform(sample_text)
        sym_name = "None"
        if symbol_id:
            sym_obj = get_symbol(symbol_id)
            if sym_obj:
                styled = sym_obj.apply(styled)
                sym_name = sym_obj.name

        embed = discord.Embed(
            title="Style Preview",
            description=(
                f"**Font #{font_obj.font_id}**: {font_obj.name}\n"
                f"**Symbol**: {sym_name}\n\n"
                f"**Input** : `{sample_text}`\n"
                f"**Output**: `{styled}`"
            ),
            colour=discord.Colour.dark_green(),
        )
        await ctx.send(embed=embed)
