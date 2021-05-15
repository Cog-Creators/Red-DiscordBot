import datetime
import heapq
import logging
import math
import random
from pathlib import Path

import discord
import lavalink

from redbot.core import commands
from redbot.core.i18n import Translator
from redbot.core.utils import AsyncIter
from redbot.core.utils._dpy_menus_utils import dpymenu
from redbot.core.utils.chat_formatting import humanize_number, pagify
from redbot.core.utils.menus import DEFAULT_CONTROLS

from ..abc import MixinMeta
from ..cog_utils import CompositeMetaClass

log = logging.getLogger("red.cogs.Audio.cog.Commands.miscellaneous")
_ = Translator("Audio", Path(__file__))


class MiscellaneousCommands(MixinMeta, metaclass=CompositeMetaClass):
    @commands.command(name="sing")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_sing(self, ctx: commands.Context):
        """Make Red sing one of her songs."""
        ids = (
            "zGTkAVsrfg8",
            "cGMWL8cOeAU",
            "vFrjMq4aL-g",
            "WROI5WYBU_A",
            "41tIUr_ex3g",
            "f9O2Rjn1azc",
        )
        url = f"https://www.youtube.com/watch?v={random.choice(ids)}"
        await ctx.invoke(self.command_play, query=url)

    @commands.command(name="audiostats")
    @commands.guild_only()
    @commands.is_owner()
    @commands.bot_has_permissions(embed_links=True, add_reactions=True)
    async def command_audiostats(self, ctx: commands.Context):
        """Audio stats."""
        server_num = len(lavalink.active_players())
        total_num = len(lavalink.all_live_players())

        msg = ""
        async for p in AsyncIter(lavalink.all_live_players()):
            connect_dur = self.get_time_string(
                int(
                    (datetime.datetime.now(datetime.timezone.utc) - p.connected_at).total_seconds()
                )
            )
            try:
                if not p.current:
                    raise AttributeError
                current_title = await self.get_track_description(
                    p.current, self.local_folder_current_path
                )
                msg += "{} [`{}`]: {}\n".format(p.channel.guild.name, connect_dur, current_title)
            except AttributeError:
                msg += "{} [`{}`]: **{}**\n".format(
                    p.channel.guild.name, connect_dur, _("Nothing playing.")
                )

        if total_num == 0:
            return await self.send_embed_msg(ctx, title=_("Not connected anywhere."))
        servers_embed = []
        pages = 1
        for page in pagify(msg, delims=["\n"], page_length=1500):
            em = discord.Embed(
                colour=await ctx.embed_colour(),
                title=_("Playing in {num}/{total} servers:").format(
                    num=humanize_number(server_num), total=humanize_number(total_num)
                ),
                description=page,
            )
            em.set_footer(
                text=_("Page {}/{}").format(
                    humanize_number(pages), humanize_number((math.ceil(len(msg) / 1500)))
                )
            )
            pages += 1
            servers_embed.append(em)

        await dpymenu(ctx, servers_embed, DEFAULT_CONTROLS)

    @commands.command(name="percent")
    @commands.guild_only()
    @commands.bot_has_permissions(embed_links=True)
    async def command_percent(self, ctx: commands.Context):
        """Queue percentage."""
        if not self._player_check(ctx):
            return await self.send_embed_msg(ctx, title=_("Nothing playing."))
        player = lavalink.get_player(ctx.guild.id)
        queue_tracks = player.queue
        requesters = {"total": 0, "users": {}}

        async def _usercount(req_username):
            if req_username in requesters["users"]:
                requesters["users"][req_username]["songcount"] += 1
                requesters["total"] += 1
            else:
                requesters["users"][req_username] = {}
                requesters["users"][req_username]["songcount"] = 1
                requesters["total"] += 1

        async for track in AsyncIter(queue_tracks):
            req_username = "{}#{}".format(track.requester.name, track.requester.discriminator)
            await _usercount(req_username)

        try:
            req_username = "{}#{}".format(
                player.current.requester.name, player.current.requester.discriminator
            )
            await _usercount(req_username)
        except AttributeError:
            return await self.send_embed_msg(ctx, title=_("There's  nothing in the queue."))

        async for req_username in AsyncIter(requesters["users"]):
            percentage = float(requesters["users"][req_username]["songcount"]) / float(
                requesters["total"]
            )
            requesters["users"][req_username]["percent"] = round(percentage * 100, 1)

        top_queue_users = heapq.nlargest(
            20,
            [
                (x, requesters["users"][x][y])
                for x in requesters["users"]
                for y in requesters["users"][x]
                if y == "percent"
            ],
            key=lambda x: x[1],
        )
        queue_user = ["{}: {:g}%".format(x[0], x[1]) for x in top_queue_users]
        queue_user_list = "\n".join(queue_user)
        await self.send_embed_msg(
            ctx, title=_("Queued and playing tracks:"), description=queue_user_list
        )
