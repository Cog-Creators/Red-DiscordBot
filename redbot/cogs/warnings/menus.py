from __future__ import annotations

from typing import Union, Dict, List, Any, Tuple, Iterable

import discord

from redbot.core.i18n import Translator

from redbot.core.utils._dpy_menus_utils import SimpleHybridMenu
from redbot.vendored.discord.ext import menus

_ = Translator("Warnings", __file__)


class ReasonListSource(menus.ListPageSource):
    def __init__(self, entries: Iterable[Tuple[str, Dict]]):
        super().__init__(entries, per_page=1)

    async def format_page(
        self, menu: SimpleHybridMenu, entry: Tuple[str, Dict]
    ) -> Union[discord.Embed, str]:
        reason, data = entry
        if await menu.ctx.embed_requested():
            message = discord.Embed(
                title=_("Reason: {name}").format(name=reason), description=data["description"],
            )
            message.add_field(name=_("Points"), value=str(data["points"]))
        else:
            message = _(
                "Name: {reason_name}\nPoints: {points}\nDescription: {description}"
            ).format(reason_name=reason, **data)

        return message


class ActionListSource(menus.ListPageSource):
    def __init__(self, entries: List[Dict[str, Any]]):
        super().__init__(entries, per_page=1)

    async def format_page(
        self, menu: SimpleHybridMenu, entry: Dict[str, str]
    ) -> Union[discord.Embed, str]:
        if await menu.ctx.embed_requested():
            message = discord.Embed(title=_("Action: {name}").format(name=entry["action_name"]))
            message.add_field(name=_("Points"), value="{}".format(entry["points"]), inline=False)
            message.add_field(
                name=_("Exceed command"), value=entry["exceed_command"], inline=False,
            )
            message.add_field(name=_("Drop command"), value=entry["drop_command"], inline=False)
        else:
            message = _(
                "Name: {action_name}\nPoints: {points}\n"
                "Exceed command: {exceed_command}\nDrop command: {drop_command}"
            ).format(**entry)

        return message
