from discord.ext import commands
from .utils.dataIO import fileIO
import os


class Seen:
    """Check when someone was last seen."""
    def __init__(self, bot):
        self.bot = bot
        self.seen_path = 'data/seen/seen.json'

    async def seen_loop(self, message):
        try:
            seen = fileIO(self.seen_path, "load")
            server_id = message.server.id
            channel_mention = message.channel.mention
            user_id = message.author.mention
            user_name = message.author.name
            last_msg = message.content
            timestamp = message.timestamp
            if server_id not in seen:
                seen[server_id] = {}
            if user_id not in seen[server_id]:
                seen[server_id][user_id] = {}
            seen[server_id][user_id]['USERNAME'] = user_name
            seen[server_id][user_id]['TIMESTAMP'] = str(timestamp)[:-7]
            seen[server_id][user_id]['MESSAGE'] = last_msg
            seen[server_id][user_id]['CHANNEL'] = channel_mention
            fileIO(self.seen_path, "save", seen)
        except:
            pass

    @commands.command(pass_context=True, no_pm=True, aliases=['s'])
    async def seen(self, context, username: str):
        """seen <@username>"""
        seen = fileIO(self.seen_path, "load")
        server_id = context.message.server.id
        username = username.replace('!', '')
        if server_id in seen:
            if username in seen[server_id]:
                timestamp = seen[server_id][username]['TIMESTAMP']
                last_msg = seen[server_id][username]['MESSAGE']
                user_name = seen[server_id][username]['USERNAME']
                channel_name = seen[server_id][username]['CHANNEL']
                message = '{0} was last seen on `{1} UTC` in {2}, saying: {3}'.format(user_name, timestamp, channel_name, last_msg)
            else:
                message = 'I have not seen {0} yet.'.format(username)
        else:
            message = 'I haven\'t seen anyone in this server yet!'
        await self.bot.say('{0}'.format(message))


def check_folder():
    if not os.path.exists("data/seen"):
        print("Creating data/seen folder...")
        os.makedirs("data/seen")


def check_file():
    data = {}
    f = "data/seen/seen.json"
    if not fileIO(f, "check"):
        print("Creating default seen.json...")
        fileIO(f, "save", data)


def setup(bot):
    check_folder()
    check_file()
    check_folder()
    check_file()
    n = Seen(bot)
    bot.add_listener(n.seen_loop, "on_message")
    bot.add_cog(n)
