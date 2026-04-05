import contextlib
from pathlib import Path

import discord

from redbot.core import commands
from redbot.core.i18n import Translator

_ = Translator("Audio", Path(__file__))


class NowPlayingView(discord.ui.View):
    """Button-based controls for the [p]now command.

    Only shown when [p]set usebuttons is enabled.
    When there is no queue and autoplay is off, prev and next are hidden.
    """

    def __init__(self, ctx: commands.Context, cog, has_queue: bool):
        super().__init__(timeout=30.0)
        self.ctx = ctx
        self.cog = cog
        self.message: discord.Message = None

        if not has_queue:
            self.remove_item(self.button_prev)
            self.remove_item(self.button_next)

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user != self.ctx.author:
            await interaction.response.send_message(
                _("You are not the one who requested this player."), ephemeral=True
            )
            return False
        return True

    async def on_timeout(self) -> None:
        if self.message:
            with contextlib.suppress(discord.HTTPException):
                await self.message.edit(view=None)

    @discord.ui.button(
        emoji="\N{BLACK LEFT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}",
        style=discord.ButtonStyle.grey,
    )
    async def button_prev(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        self.stop()
        with contextlib.suppress(discord.HTTPException):
            await self.message.edit(view=None)
        await self.ctx.invoke(self.cog.command_prev)

    @discord.ui.button(
        emoji="\N{BLACK SQUARE FOR STOP}\N{VARIATION SELECTOR-16}",
        style=discord.ButtonStyle.grey,
    )
    async def button_stop(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        self.stop()
        with contextlib.suppress(discord.HTTPException):
            await self.message.edit(view=None)
        await self.ctx.invoke(self.cog.command_stop)

    @discord.ui.button(
        emoji="\N{BLACK RIGHT-POINTING TRIANGLE WITH DOUBLE VERTICAL BAR}\N{VARIATION SELECTOR-16}",
        style=discord.ButtonStyle.grey,
    )
    async def button_pause(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        self.stop()
        with contextlib.suppress(discord.HTTPException):
            await self.message.edit(view=None)
        await self.ctx.invoke(self.cog.command_pause)

    @discord.ui.button(
        emoji="\N{BLACK RIGHT-POINTING DOUBLE TRIANGLE WITH VERTICAL BAR}\N{VARIATION SELECTOR-16}",
        style=discord.ButtonStyle.grey,
    )
    async def button_next(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        self.stop()
        with contextlib.suppress(discord.HTTPException):
            await self.message.edit(view=None)
        await self.ctx.invoke(self.cog.command_skip)

    @discord.ui.button(
        emoji="\N{CROSS MARK}",
        style=discord.ButtonStyle.grey,
    )
    async def button_close(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ):
        await interaction.response.defer()
        self.stop()
        with contextlib.suppress(discord.HTTPException):
            await self.message.delete()
