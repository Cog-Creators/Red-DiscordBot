from __future__ import annotations

from typing import Union, Dict, List

import discord

from redbot.core.i18n import Translator

from redbot.core.utils._dpy_menus_utils import SimpleHybridMenu
from redbot.vendored.discord.ext import menus

_ = Translator("General", __file__)


class UrbanSource(menus.ListPageSource):
    def __init__(self, entries: List[Dict[str, str]]):
        super().__init__(entries, per_page=1)

    async def format_page(
        self, menu: SimpleHybridMenu, entry: Dict[str, str]
    ) -> Union[discord.Embed, str]:
        if await menu.ctx.embed_requested():
            message = discord.Embed(colour=await menu.ctx.embed_colour())
            message.title = _("{word} by {author}").format(
                word=entry["word"].capitalize(), author=entry["author"]
            )
            message.url = entry["permalink"]

            description = _("{definition}\n\n**Example:** {example}").format(**entry)
            if len(description) > 2048:
                description = "{}...".format(description[:2045])
            message.description = description

            message.set_footer(
                text=_("{thumbs_down} Down / {thumbs_up} Up, Powered by Urban Dictionary.").format(
                    **entry
                )
            )
        else:
            entry.setdefault("example", "N/A")
            message = _(
                "<{permalink}>\n {word} by {author}\n\n{description}\n\n"
                "{thumbs_down} Down / {thumbs_up} Up, Powered by Urban Dictionary."
            ).format(word=entry.pop("word").capitalize(), description="{description}", **entry)
            max_desc_len = 2000 - len(message)

            description = _("{definition}\n\n**Example:** {example}").format(**entry)
            if len(description) > max_desc_len:
                description = "{}...".format(description[: max_desc_len - 3])

            message = message.format(description=description)

        return message
