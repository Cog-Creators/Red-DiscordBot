import discord

from collections import defaultdict, deque

from redbot.core.bot import Red
from redbot.core.config import Config


async def is_allowed_by_hierarchy(
    bot: Red, config: Config, guild: discord.Guild, mod: discord.Member, user: discord.Member
):
    if not await config.guild(guild).respect_hierarchy():
        return True
    is_special = mod == guild.owner or await bot.is_owner(mod)
    return mod.top_role > user.top_role or is_special


async def create_new_cache(config: Config, guild: discord.Guild):
    repeats = await config.guild(guild).delete_repeats()
    guild_cache = (
        defaultdict(lambda: defaultdict(lambda: deque(maxlen=repeats)))
        if repeats != -1
        else dict()
    )

    # Create already keys for custom amount of repeated messages per channel
    repeats_channels = await config.guild(guild).delete_repeats_channels.all()
    print(repeats_channels)
    for key, value in repeats_channels.items():
        print(f"{key}:{value}")
        print(type(key))
        if int(value) > 0:
            guild_cache[key] = defaultdict(lambda: deque(maxlen=int(value)))

    return guild_cache
