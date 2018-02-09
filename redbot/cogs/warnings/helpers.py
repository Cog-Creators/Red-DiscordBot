import asyncio
import discord

from redbot.core import RedContext, Config
from redbot.core.utils.chat_formatting import warning


async def warning_points_add_check(config: Config, ctx: RedContext, user: discord.Member, points: int):
    """Handles any action that needs to be taken or not based on the points"""
    guild = ctx.guild
    guild_settings = config.guild(guild)
    act = {}
    async with guild_settings.actions() as registered_actions:
        for a in registered_actions.keys():
            if points >= registered_actions[a]["point_count"]:
                act = registered_actions[a]
            else:
                break
    if act:  # some action needs to be taken
        command = ctx.bot.get_command(act["exceed_command"]["name"])
        kwargs = act["exceed_command"]["kwargs"]
        if "user" in kwargs:
            kwargs["user"] = user
        elif "member" in kwargs:
            kwargs["member"] = user
        if command is None:
            await ctx.send(
                warning("I could not execute the command `{}` because I could not find it!")
            )
            return

        await ctx.invoke(command, **kwargs)


async def get_command_for_exceeded_points(ctx: RedContext):
    """Gets the command to be executed when the user is at or exceeding
    the points threshold for the action"""
    await ctx.send(
        "Enter the command to be run when the user "
        "exceeds the points for this action to occur. "
        "Enter only the command (do not enter its arguments)."
    )

    def same_author_check(m):
        return m.author == ctx.author

    try:
        msg = await ctx.bot.wait_for("message", check=same_author_check, timeout=30)
    except asyncio.TimeoutError:
        await ctx.send("Ok then.")
        return None

    command = ctx.bot.get_command(msg.content)
    if command is None:
        await ctx.send("That isn't a command!")
        return None

    params = command.clean_params
    kwargs = {}
    for param in params:
        if param == "user" or param == "member":  # to be filled in at runtime
            kwargs[param] = None
            continue
        await ctx.send("Enter the value for the `{}` parameter".format(param))
        try:
            msg = await ctx.bot.wait_for("message", check=same_author_check, timeout=30)
        except asyncio.TimeoutError:
            await ctx.send("Ok then.")
            return None
        kwargs[param] = msg.content

    cmd_info = {
        "name": command.qualified_name,
        "kwargs": kwargs
    }
    return cmd_info


async def get_command_for_dropping_points(ctx: RedContext):
    """
    Gets the command to be executed when the user drops below the points
    threshold

    This is intended to be used for reversal of the action that was executed
    when the user exceeded the threshold
    """
    pass
