import discord
from discord.ext import commands
from .utils.chat_formatting import box


class ServerInfo:
    "Commands to show basic information"
    def __init__(self, bot):
        self.bot = bot

    @commands.command(pass_context=True, allow_pm=False)
    async def sinfo(self, ctx):
        "Show server , owner and channel info"
        server = ctx.message.server
        channel = ctx.message.channel
        members = set(server.members)

        owner = server.owner

        offline = filter(lambda m: m.status is discord.Status.offline, members)
        offline = set(offline)

        bots = filter(lambda m: m.bot, members)
        bots = set(bots)

        users = members - bots

        msg = '\n'.join((
            'Server Name     : ' + server.name,
            'Server ID       : ' + str(server.id),
            'Server Created  : ' + str(server.created_at),
            'Server Region   : ' + str(server.region),
            'Verification    : ' + str(server.verification_level),
            # minus one for @everyone
            'Server # Roles  : %i' % (len(server.roles) - 1),
            '',
            'Server Owner    : ' + (
                ('{0.nick} ({0})'.format(owner)) if owner.nick
                else str(owner)),
            'Owner ID        : ' + str(owner.id),
            'Owner Status    : ' + str(owner.status),
            '',
            'Total Bots      : %i' % len(bots),
            'Bots Online     : %i' % len(bots - offline),
            'Bots Offline    : %i' % len(bots & offline),
            '',
            'Total Users     : %i' % len(users),
            'Users Online    : %i' % len(users - offline),
            'Users Offline   : %i' % len(users & offline),
            '',
            'Current Channel : #' + channel.name,
            'Channel ID      : ' + str(channel.id),
            'Channel Created : ' + str(channel.created_at)
        ))
        await self.bot.say(box(msg))


def setup(bot):
    m = ServerInfo(bot)
    bot.add_cog(m)
