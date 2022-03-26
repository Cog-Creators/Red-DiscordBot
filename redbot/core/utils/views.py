from __future__ import annotations

import discord

from discord.ext.commands import BadArgument
from typing import TYPE_CHECKING, List, Dict, Union, Optional
from redbot.core.commands.converter import get_dict_converter
from redbot.core.i18n import Translator

if TYPE_CHECKING:
    from redbot.core.bot import Red

_ = Translator("UtilsViews", __file__)


class SetApiModal(discord.ui.Modal):
    def __init__(
        self,
        bot: Red,
        default_service: Optional[str] = None,
        default_keys: Optional[Dict[str, str]] = None,
    ):
        self.bot: Red = bot
        self.default_service = default_service
        self.default_keys: List[str] = []
        if default_keys is not None:
            self.default_keys = list(default_keys.keys())
        self.default_keys_fmt = self._format_keys(default_keys)

        _placeholder_service = "service"
        if self.default_service is not None:
            _placeholder_service = self.default_service
        _placeholder_token = "client_id YOUR_CLIENT_ID"
        if self.default_keys_fmt is not None:
            _placeholder_token = self.default_keys_fmt

        self.title = _("Set API Keys")
        self.keys_label = _("Keys and tokens")
        if self.default_service is not None:
            self.title = _("Set API Keys for {service}").format(service=self.default_service)
            self.keys_label = _("Keys and tokens for {service}").format(
                service=self.default_service
            )
            self.default_service = self.default_service.lower()
            # Lower here to prevent someone from capitalizing a service name for the sake of UX.

        super().__init__(title=self.title)

        self.service_input = discord.ui.TextInput(
            label=_("Service"),
            required=True,
            placeholder=_placeholder_service,
            default=self.default_service,
        )

        self.token_input = discord.ui.TextInput(
            label=self.keys_label,
            style=discord.TextStyle.long,
            required=True,
            placeholder=_placeholder_token,
            default=self.default_keys_fmt,
        )

        if self.default_service is None:
            self.add_item(self.service_input)
        self.add_item(self.token_input)

    @staticmethod
    def _format_keys(keys: Optional[Dict[str, str]]) -> Optional[str]:
        """Format the keys to be used on a long discord.TextInput format"""
        if keys is not None:
            ret = ""
            for k, v in keys.items():
                if v:
                    ret += f"{k} {v}\n"
                else:
                    ret += f"{k} YOUR_{k.upper()}\n"
            return ret
        else:
            return None

    async def on_submit(self, interaction: discord.Interaction):
        if (
            await self.bot.is_owner(interaction.user) is False
        ):  # Prevent non-bot owners from somehow aquiring and saving the modal.
            return await interaction.response.send_message(
                _("This modal is for bot owners only. Whoops!"), ephemeral=True
            )

        if self.default_keys is not None:
            converter = get_dict_converter(*self.default_keys, delims=[";", ",", " "])
        else:
            converter = get_dict_converter(delims=[";", ",", " "])
        tokens = " ".join(self.token_input.value.split("\n")).rstrip()

        try:
            tokens = await converter().convert(None, tokens)
        except BadArgument as exc:
            return await interaction.response.send_message(
                _("{error_message}\nPlease try again.").format(error_message=str(exc)),
                ephemeral=True,
            )

        if self.default_service is not None:  # Check is there is a service set.
            await self.bot.set_shared_api_tokens(self.default_service, **tokens)
            return await interaction.response.send_message(
                _("`{service}` API tokens have been set.").format(service=self.default_service),
                ephemeral=True,
            )
        else:
            service = self.service_input.value.lower()
            await self.bot.set_shared_api_tokens(service, **tokens)
            return await interaction.response.send_message(
                _("`{service}` API tokens have been set.").format(service=service),
                ephemeral=True,
            )


class SetApiView(discord.ui.View):
    def __init__(
        self,
        bot: Red,
        default_service: Optional[str] = None,
        default_keys: Optional[Union[str, List[str]]] = None,
    ):
        self.bot: Red = bot
        self.default_service = default_service
        self.default_keys = default_keys
        super().__init__()

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if await self.bot.is_owner(interaction.user) is False:
            await interaction.response.send_message(
                _("This button is for bot owners only. Oh well"), ephemeral=True
            )
            return False
        return True

    @discord.ui.button(
        label=_("Set API token"),
        style=discord.ButtonStyle.grey,
    )
    async def auth_button(self, interaction: discord.Interaction, button: discord.Button):
        return await interaction.response.send_modal(
            SetApiModal(self.bot, self.default_service, self.default_keys)
        )
