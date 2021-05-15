import asyncio
import contextlib
import logging

from typing import List

import discord
import lavalink
from lavalink.filters import Equalizer

from redbot.core import commands
from redbot.core.utils.chat_formatting import box

from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Utilities.equalizer")


class EqualizerUtilities(MixinMeta, metaclass=CompositeMetaClass):
    async def _apply_gain(self, guild_id: int, band: int, gain: float) -> None:
        const = {
            "op": "equalizer",
            "guildId": str(guild_id),
            "bands": [{"band": band, "gain": gain}],
        }

        try:
            await lavalink.get_player(guild_id).node.send({**const})
        except (KeyError, IndexError):
            pass

    async def _apply_gains(self, guild_id: int, gains: List[float]) -> None:
        const = {
            "op": "equalizer",
            "guildId": str(guild_id),
            "bands": [{"band": x, "gain": y} for x, y in enumerate(gains)],
        }

        try:
            await lavalink.get_player(guild_id).node.send({**const})
        except (KeyError, IndexError):
            pass

    async def _eq_check(self, ctx: commands.Context, player: lavalink.Player) -> None:
        config_bands = await self.config.custom("EQUALIZER", ctx.guild.id).eq_bands()
        if not config_bands:
            config_bands = player.equalizer.get()
            async with self.config.custom("EQUALIZER", ctx.guild.id).all() as eq_data:
                eq_data["eq_bands"] = config_bands
                eq_data["name"] = player.equalizer.name
        name = await self.config.custom("EQUALIZER", ctx.guild.id).name()
        if isinstance(config_bands[0], (float, int)):
            if player.equalizer.get() != config_bands:
                band_num = list(range(player.equalizer.band_count))
                band_value = config_bands
                new_eq = Equalizer(
                    levels=[
                        dict(zip(["band", "gain"], values))
                        for values in list(zip(band_num, band_value))
                    ],
                    name=name
                )
                await player.set_equalizer(equalizer=new_eq)
        else:
            new_eq = Equalizer(levels=config_bands, name=name)
            await player.set_equalizer(equalizer=new_eq)

    async def _eq_interact(
        self,
        ctx: commands.Context,
        player: lavalink.Player,
        message: discord.Message,
        selected: int,
    ) -> None:
        emoji = {
            "far_left": "\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
            "one_left": "\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}",
            "max_output": "\N{BLACK UP-POINTING DOUBLE TRIANGLE}",
            "output_up": "\N{UP-POINTING SMALL RED TRIANGLE}",
            "output_down": "\N{DOWN-POINTING SMALL RED TRIANGLE}",
            "min_output": "\N{BLACK DOWN-POINTING DOUBLE TRIANGLE}",
            "one_right": "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}",
            "far_right": "\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}",
            "reset": "\N{BLACK CIRCLE FOR RECORD}\N{VARIATION SELECTOR-16}",
            "info": "\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16}",
        }
        selector = f'{" " * 8}{"   " * selected}^^'
        try:
            await message.edit(
                content=box(f"{player.equalizer.visualise()}\n{selector}", lang="ini")
            )
        except discord.errors.NotFound:
            return
        try:
            (react_emoji, react_user) = await self._get_eq_reaction(ctx, message, emoji)
        except TypeError:
            return

        if not react_emoji:
            async with await self.config.custom("EQUALIZER", ctx.guild.id).all() as eq_data:
                eq_data["eq_bands"] = player.equalizer.get()
                eq_data["name"] = player.equalizer.name
            await self._clear_react(message, emoji)

        if react_emoji == "\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}":
            await self.remove_react(message, react_emoji, react_user)
            await self._eq_interact(ctx, player, message, max(selected - 1, 0))

        if react_emoji == "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}":
            await self.remove_react(message, react_emoji, react_user)
            await self._eq_interact(ctx, player, message, min(selected + 1, 14))

        if react_emoji == "\N{UP-POINTING SMALL RED TRIANGLE}":
            await self.remove_react(message, react_emoji, react_user)
            _max = float("{:.2f}".format(min(player.equalizer.get_gain(selected) + 0.1, 1.0)))
            player.equalizer.set_gain(selected, _max)
            await player.set_equalizer(equalizer=player.equalizer)
            await self._eq_interact(ctx, player, message, selected)

        if react_emoji == "\N{DOWN-POINTING SMALL RED TRIANGLE}":
            await self.remove_react(message, react_emoji, react_user)
            _min = float("{:.2f}".format(max(player.equalizer.get_gain(selected) - 0.1, -0.25)))
            player.equalizer.set_gain(selected, _min)
            await player.set_equalizer(equalizer=player.equalizer)
            await self._eq_interact(ctx, player, message, selected)

        if react_emoji == "\N{BLACK UP-POINTING DOUBLE TRIANGLE}":
            await self.remove_react(message, react_emoji, react_user)
            _max = 1.0
            player.equalizer.set_gain(selected, _max)
            await self._apply_gain(ctx.guild.id, selected, _max)
            await self._eq_interact(ctx, player, message, selected)

        if react_emoji == "\N{BLACK DOWN-POINTING DOUBLE TRIANGLE}":
            await self.remove_react(message, react_emoji, react_user)
            _min = -0.25
            player.equalizer.set_gain(selected, _min)
            await self._apply_gain(ctx.guild.id, selected, _min)
            await self._eq_interact(ctx, player, message, selected)

        if react_emoji == "\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}":
            await self.remove_react(message, react_emoji, react_user)
            selected = 0
            await self._eq_interact(ctx, player, message, selected)

        if react_emoji == "\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}":
            await self.remove_react(message, react_emoji, react_user)
            selected = 14
            await self._eq_interact(ctx, player, message, selected)

        if react_emoji == "\N{BLACK CIRCLE FOR RECORD}\N{VARIATION SELECTOR-16}":
            await self.remove_react(message, react_emoji, react_user)
            player.equalizer.reset()
            await player.set_equalizer(equalizer=player.equalizer)
            await self._eq_interact(ctx, player, message, selected)

        if react_emoji == "\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16}":
            await self.remove_react(message, react_emoji, react_user)
            await ctx.send_help(self.command_equalizer)
            await self._eq_interact(ctx, player, message, selected)

    async def _eq_msg_clear(self, eq_message: discord.Message):
        if eq_message is not None:
            with contextlib.suppress(discord.HTTPException):
                await eq_message.delete()

    async def _get_eq_reaction(self, ctx: commands.Context, message: discord.Message, emoji):
        try:
            reaction, user = await self.bot.wait_for(
                "reaction_add",
                check=lambda r, u: r.message.id == message.id
                and u.id == ctx.author.id
                and r.emoji in emoji.values(),
                timeout=30,
            )
        except asyncio.TimeoutError:
            await self._clear_react(message, emoji)
            return None
        else:
            return reaction.emoji, user
