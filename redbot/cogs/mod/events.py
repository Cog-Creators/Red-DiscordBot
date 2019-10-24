import logging
from datetime import datetime
from collections import defaultdict, deque

import discord
from redbot.core import i18n, modlog, commands
from redbot.core.utils.mod import is_mod_or_superior
from .abc import MixinMeta

_ = i18n.Translator("Mod", __file__)
log = logging.getLogger("red.mod")


class Events(MixinMeta):
    """
    This is a mixin for the core mod cog
    Has a bunch of things split off to here.
    """

    async def check_duplicates(self, message):
        guild = message.guild
        author = message.author

        guild_cache = self.cache.get(guild.id, None)
        if guild_cache is None:
            repeats = await self.settings.guild(guild).delete_repeats()
            if repeats == -1:
                return False
            guild_cache = self.cache[guild.id] = defaultdict(lambda: deque(maxlen=repeats))

        if not message.content:
            return False

        guild_cache[author].append(message.content)
        msgs = guild_cache[author]
        if len(msgs) == msgs.maxlen and len(set(msgs)) == 1:
            try:
                await message.delete()
                return True
            except discord.HTTPException:
                pass
        return False

    async def check_mention_spam(self, message):
        guild = message.guild
        author = message.author

        max_mentions = await self.settings.guild(guild).ban_mention_spam()
        if max_mentions:
            mentions = set(message.mentions)
            if len(mentions) >= max_mentions:
                try:
                    await guild.ban(author, reason=_("Mention spam (Autoban)"))
                except discord.HTTPException:
                    log.info(
                        "Failed to ban member for mention spam in server {}.".format(guild.id)
                    )
                else:
                    try:
                        await modlog.create_case(
                            self.bot,
                            guild,
                            message.created_at,
                            "ban",
                            author,
                            guild.me,
                            _("Mention spam (Autoban)"),
                            until=None,
                            channel=None,
                        )
                    except RuntimeError as e:
                        print(e)
                        return False
                    return True
        return False

    @commands.Cog.listener()
    async def on_message(self, message):
        author = message.author
        if message.guild is None or self.bot.user == author:
            return
        valid_user = isinstance(author, discord.Member) and not author.bot
        if not valid_user:
            return

        #  Bots and mods or superior are ignored from the filter
        mod_or_superior = await is_mod_or_superior(self.bot, obj=author)
        if mod_or_superior:
            return
        # As are anyone configured to be
        if await self.bot.is_automod_immune(message):
            return
        deleted = await self.check_duplicates(message)
        if not deleted:
            await self.check_mention_spam(message)

    @commands.Cog.listener()
    async def on_user_update(self, before: discord.User, after: discord.User):
        if before.name != after.name:
            async with self.settings.user(before).past_names() as name_list:
                while None in name_list:  # clean out null entries from a bug
                    name_list.remove(None)
                if after.name in name_list:
                    # Ensure order is maintained without duplicates occuring
                    name_list.remove(after.name)
                name_list.append(after.name)
                while len(name_list) > 20:
                    name_list.pop(0)

    @commands.Cog.listener()
    async def on_member_update(self, before: discord.Member, after: discord.Member):
        if before.nick != after.nick and after.nick is not None:
            async with self.settings.member(before).past_nicks() as nick_list:
                while None in nick_list:  # clean out null entries from a bug
                    nick_list.remove(None)
                if after.nick in nick_list:
                    nick_list.remove(after.nick)
                nick_list.append(after.nick)
                while len(nick_list) > 20:
                    nick_list.pop(0)
