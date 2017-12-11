import discord

import random


def random_colour() -> discord.Colour:
    """
    Get a random colour for use in an embed
    There is an alias for this called random_color

    Returns
    -------
    discord.Colour
        The random colour
    """
    return discord.Color(
        value=int(
            ''.join([random.choice('0123456789ABCDEF') for x in range(6)]), 16
        )
    )


random_color = random_colour
