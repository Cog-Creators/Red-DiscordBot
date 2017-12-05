import discord
from discord.ext import commands
from collections import namedtuple
from cogs.utils.chat_formatting import escape, pagify

# Commission made for ScarletRaven, who decided to make it public
# for everyone to enjoy 👍

OpenRift = namedtuple("Rift", ["source", "destination"])


class Rift:
    """Communicate with other servers/channels!"""

    def __init__(self, bot):
        self.bot = bot
        self.open_rifts = {}

    @commands.command(pass_context=True)
    async def riftopen(self, ctx, channel):
        """Makes you able to communicate with other channels through Red

        This is cross-server. Type only the channel name or the ID."""
        author = ctx.message.author
        author_channel = ctx.message.channel

        def check(m):
            try:
                return channels[int(m.content)]
            except:
                return False

        channels = self.bot.get_all_channels()
        channels = [c for c in channels
                    if c.name.lower() == channel or c.id == channel]
        channels = [c for c in channels if c.type == discord.ChannelType.text]


        if not channels:
            await self.bot.say("No channels found. Remember to type just "
                               "the channel name, no `#`.")
            return

        if len(channels) > 1:
            msg = "Multiple results found.\nChoose a server:\n"
            for i, channel in enumerate(channels):
                msg += "{} - {} ({})\n".format(i, channel.server, channel.id)
            for page in pagify(msg):
                await self.bot.say(page)
            choice = await self.bot.wait_for_message(author=author,
                                                     timeout=30,
                                                     check=check,
                                                     channel=author_channel)
            if choice is None:
                await self.bot.say("You haven't chosen anything.")
                return
            channel = channels[int(choice.content)]
        else:
            channel = channels[0]

        rift = OpenRift(source=author_channel, destination=channel)

        self.open_rifts[author] = rift
        await self.bot.say("A rift has been opened! Everything you say "
                           "will be relayed to that channel.\n"
                           "Responses will be relayed here.\nType "
                           "`exit` to quit.")
        msg = ""
        while msg == "" or msg is not None:
            msg = await self.bot.wait_for_message(author=author,
                                                  channel=author_channel)
            if msg is not None and msg.content.lower() != "exit":
                try:
                    await self.bot.send_message(channel, msg.content)
                except:
                    await self.bot.say("Couldn't send your message.")
            else:
                break
        del self.open_rifts[author]
        await self.bot.say("Rift closed.")

    async def on_message(self, message):
        if message.author == self.bot.user:
            return
        for k, v in self.open_rifts.items():
            if v.destination == message.channel:
                msg = "{}: {}".format(message.author, message.content)
                msg = escape(msg, mass_mentions=True)
                await self.bot.send_message(v.source, msg)


def setup(bot):
    bot.add_cog(Rift(bot))
