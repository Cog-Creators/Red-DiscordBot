"""Batch renaming engine for applying typography across guild channels and roles."""

import asyncio
from typing import Callable, Dict, List, Optional, Tuple

import discord
from discord.ext import commands

from .constants import MAX_DISCORD_NAME_LENGTH, RENAMING_DELAY_SECONDS


class ServerStyleApplier:
    """Manages batch inspection, transformation, snapshotting, and renaming of guild elements."""

    def __init__(self, guild: discord.Guild):
        self.guild = guild

    @staticmethod
    def clean_channel_name(name: str, is_text_channel: bool = False) -> str:
        """Sanitizes transformed name within Discord's length and character boundaries."""
        sanitized = name.strip()[:MAX_DISCORD_NAME_LENGTH]
        if is_text_channel:
            # Replace spaces with hyphens for standard Discord text channel formatting
            sanitized = sanitized.replace(" ", "-")
        return sanitized

    def collect_elements(
        self, scope: int
    ) -> Tuple[List[discord.abc.GuildChannel], List[discord.Role]]:
        """Collects targets according to selected scope (1: Text, 2: Voice, 3: Categories, 4: Roles, 5: All)."""
        channels: List[discord.abc.GuildChannel] = []
        roles: List[discord.Role] = []

        if scope in (1, 5):
            channels.extend(self.guild.text_channels)
        if scope in (2, 5):
            channels.extend(self.guild.voice_channels)
        if scope in (3, 5):
            channels.extend(self.guild.categories)
        if scope in (4, 5):
            # Exclude @everyone and managed bot roles
            roles.extend(
                [
                    r
                    for r in self.guild.roles
                    if not r.is_default() and not r.managed and r < self.guild.me.top_role
                ]
            )

        return channels, roles

    def build_preview(
        self,
        channels: List[discord.abc.GuildChannel],
        roles: List[discord.Role],
        transform_fn: Callable[[str], str],
        max_samples: int = 5,
    ) -> List[str]:
        """Builds a sample before/after preview for the user."""
        preview_lines = []
        sample_channels = channels[:max_samples]
        for ch in sample_channels:
            is_text = isinstance(ch, discord.TextChannel)
            styled = self.clean_channel_name(transform_fn(ch.name), is_text_channel=is_text)
            preview_lines.append(f"Channel: #{ch.name} -> #{styled}")

        sample_roles = roles[:max_samples]
        for r in sample_roles:
            styled = transform_fn(r.name)[:MAX_DISCORD_NAME_LENGTH]
            preview_lines.append(f"Role: @{r.name} -> @{styled}")

        remaining = (len(channels) + len(roles)) - (len(sample_channels) + len(sample_roles))
        if remaining > 0:
            preview_lines.append(f"... and {remaining} more elements.")

        return preview_lines

    async def apply_batch(
        self,
        ctx: commands.Context,
        channels: List[discord.abc.GuildChannel],
        roles: List[discord.Role],
        transform_fn: Callable[[str], str],
    ) -> Dict[str, Dict[str, str]]:
        """Applies transformation with rate-limit pacing and returns a restoration snapshot."""
        snapshot: Dict[str, Dict[str, str]] = {"channels": {}, "roles": {}}
        total = len(channels) + len(roles)
        processed = 0

        status_msg = await ctx.send(f"Applying server styling (0/{total} completed)...")

        # 1. Channels
        for ch in channels:
            snapshot["channels"][str(ch.id)] = ch.name
            is_text = isinstance(ch, discord.TextChannel)
            new_name = self.clean_channel_name(transform_fn(ch.name), is_text_channel=is_text)
            if new_name != ch.name:
                try:
                    await ch.edit(name=new_name, reason="RayzCServe: typography styling applied")
                except discord.RateLimited as rl:
                    await asyncio.sleep(rl.retry_after)
                    await ch.edit(name=new_name, reason="RayzCServe: typography styling applied")
                except discord.Forbidden:
                    pass
                except Exception:
                    pass
                await asyncio.sleep(RENAMING_DELAY_SECONDS)

            processed += 1
            if processed % 5 == 0 or processed == total:
                try:
                    await status_msg.edit(
                        content=f"Applying server styling ({processed}/{total} completed)..."
                    )
                except Exception:
                    pass

        # 2. Roles
        for role in roles:
            snapshot["roles"][str(role.id)] = role.name
            new_name = transform_fn(role.name)[:MAX_DISCORD_NAME_LENGTH]
            if new_name != role.name:
                try:
                    await role.edit(name=new_name, reason="RayzCServe: typography styling applied")
                except discord.RateLimited as rl:
                    await asyncio.sleep(rl.retry_after)
                    await role.edit(name=new_name, reason="RayzCServe: typography styling applied")
                except discord.Forbidden:
                    pass
                except Exception:
                    pass
                await asyncio.sleep(RENAMING_DELAY_SECONDS)

            processed += 1
            if processed % 5 == 0 or processed == total:
                try:
                    await status_msg.edit(
                        content=f"Applying server styling ({processed}/{total} completed)..."
                    )
                except Exception:
                    pass

        try:
            await status_msg.edit(
                content=f"Batch typography styling complete. Total elements styled: {total}."
            )
        except Exception:
            pass

        return snapshot

    @staticmethod
    async def revert_snapshot(
        guild: discord.Guild, snapshot: Dict[str, Dict[str, str]]
    ) -> Tuple[int, int]:
        """Reverts channels and roles to their original names from the provided snapshot."""
        reverted_channels = 0
        reverted_roles = 0

        # Revert Channels
        channel_map = snapshot.get("channels", {})
        for ch_id_str, original_name in channel_map.items():
            ch = guild.get_channel(int(ch_id_str))
            if ch and ch.name != original_name:
                try:
                    await ch.edit(name=original_name, reason="RayzCServe: undo styling")
                    reverted_channels += 1
                    await asyncio.sleep(RENAMING_DELAY_SECONDS)
                except Exception:
                    pass

        # Revert Roles
        role_map = snapshot.get("roles", {})
        for role_id_str, original_name in role_map.items():
            role = guild.get_role(int(role_id_str))
            if role and role.name != original_name:
                try:
                    await role.edit(name=original_name, reason="RayzCServe: undo styling")
                    reverted_roles += 1
                    await asyncio.sleep(RENAMING_DELAY_SECONDS)
                except Exception:
                    pass

        return reverted_channels, reverted_roles
