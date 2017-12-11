import discord

import random


def randomize_colour(embed: discord.Embed) -> discord.Embed:
    """
    Gives the provided embed a random color.
    There is an alias for this called randomize_color

    Parameters
    ----------
    embed : discord.Embed
        The embed to add a color to

    Returns
    -------
    discord.Embed
        The embed with the color set to a random color

    """
    embed.colour = discord.Color(
        value=int(
            ''.join([random.choice('0123456789ABCDEF') for x in range(6)]), 16
        )
    )
    return embed


randomize_color = randomize_colour
