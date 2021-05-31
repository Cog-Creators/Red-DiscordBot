import asyncio
import contextlib
import logging

import discord
import lavalink
from lavalink.filters import Equalizer
from redbot.core import commands
from redbot.core.utils.chat_formatting import box

from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Utilities.equalizer")


class EqualizerUtilities(MixinMeta, metaclass=CompositeMetaClass):
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
                    name=name,
                )
                if new_eq != player.equalizer:
                    await player.set_equalizer(equalizer=new_eq)
        else:
            new_eq = Equalizer(levels=config_bands, name=name)
            if new_eq != player.equalizer:
                await player.set_equalizer(equalizer=new_eq)

    async def _eq_interact(
        self,
        ctx: commands.Context,
        player: lavalink.Player,
        message: discord.Message,
        selected: int,
        equalizer: Equalizer,
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
        async for react_emoji, react_user in self._get_eq_reaction(ctx, message, emoji):
            selector = f'{" " * 8}{"   " * selected}^^'
            try:
                await message.edit(
                    content=box(f"{player.equalizer.visualise()}\n{selector}", lang="yaml")
                )
            except discord.errors.NotFound:
                break
            MAX_PAGE = 14
            MIN_PAGE = 0
            if not react_emoji:
                async with self.config.custom("EQUALIZER", ctx.guild.id).all() as eq_data:
                    eq_data["eq_bands"] = equalizer.get()
                    eq_data["name"] = equalizer.name
                await self._clear_react(message, emoji)

            if react_emoji == "\N{LEFTWARDS BLACK ARROW}\N{VARIATION SELECTOR-16}":
                page = selected - 1
                selected = page if page > 0 else MAX_PAGE

            if react_emoji == "\N{BLACK RIGHTWARDS ARROW}\N{VARIATION SELECTOR-16}":
                page = selected + 1
                selected = page if page < 15 else MIN_PAGE
            if react_emoji == "\N{UP-POINTING SMALL RED TRIANGLE}":
                _max = float("{:.2f}".format(min(equalizer.get_gain(selected) + 0.1, 1.0)))
                equalizer.set_gain(selected, _max)
                await player.set_equalizer(equalizer=equalizer)

            if react_emoji == "\N{DOWN-POINTING SMALL RED TRIANGLE}":
                _min = float("{:.2f}".format(max(equalizer.get_gain(selected) - 0.05, -0.25)))
                equalizer.set_gain(selected, _min)
                await player.set_equalizer(equalizer=equalizer)

            if react_emoji == "\N{BLACK UP-POINTING DOUBLE TRIANGLE}":
                _max = 1.0
                equalizer.set_gain(selected, _max)
                await player.set_equalizer(equalizer=equalizer)

            if react_emoji == "\N{BLACK DOWN-POINTING DOUBLE TRIANGLE}":
                _min = -0.25
                equalizer.set_gain(selected, _min)
                await player.set_equalizer(equalizer=equalizer)

            if react_emoji == "\N{BLACK LEFT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}":
                selected = 0

            if react_emoji == "\N{BLACK RIGHT-POINTING TRIANGLE}\N{VARIATION SELECTOR-16}":
                selected = 14

            if react_emoji == "\N{BLACK CIRCLE FOR RECORD}\N{VARIATION SELECTOR-16}":
                equalizer.reset()
                await player.set_equalizer(equalizer=equalizer)

            if react_emoji == "\N{INFORMATION SOURCE}\N{VARIATION SELECTOR-16}":
                await ctx.send_help(self.command_equalizer)

    async def _eq_msg_clear(self, eq_message: discord.Message):
        if eq_message is not None:
            with contextlib.suppress(discord.HTTPException):
                await eq_message.delete()

    async def _get_eq_reaction(self, ctx: commands.Context, message: discord.Message, emoji):
        while True:
            try:
                tasks = [
                    asyncio.ensure_future(
                        self.bot.wait_for(
                            "reaction_add",
                            check=lambda r, u: r.message.id == message.id
                            and u.id == ctx.author.id
                            and r.emoji in emoji.values(),
                        )
                    ),
                    asyncio.ensure_future(
                        self.bot.wait_for(
                            "reaction_remove",
                            check=lambda r, u: r.message.id == message.id
                            and u.id == ctx.author.id
                            and r.emoji in emoji.values(),
                        )
                    ),
                ]
                done, pending = await asyncio.wait(
                    tasks, timeout=30, return_when=asyncio.FIRST_COMPLETED
                )
                for task in pending:
                    task.cancel()

                if len(done) == 0:
                    raise asyncio.TimeoutError()

                # Exception will propagate if e.g. cancelled or timed out
                reaction, user = done.pop().result()

            except asyncio.TimeoutError:
                return
            else:
                yield reaction.emoji, user
