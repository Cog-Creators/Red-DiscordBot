import os
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from difflib import SequenceMatcher


class Games:
    def __init__(self, bot):
        self.bot = bot
        self.servers = {}
        for server in os.listdir('data/games'):
            self.servers[server.split('.')[0]] = dataIO.load_json('data/games/{}'.format(server))

    def match(self, a, b):
        return SequenceMatcher(None, a, b).ratio()

    async def listener(self, before, after):
        server = after.server
        filename = 'data/games/{}.json'.format(server.id)
        if not after.bot and after.game is not None:
            p = True
            if before.game is not None and after.game is not None:
                if before.game.name == after.game.name:
                    p = False
            if len(after.game.name) > 2 and p:
                if not dataIO.is_valid_json(filename):
                    data = {}
                else:
                    try:
                        data = self.servers[server.id]
                    except KeyError:
                        data = {}
                game = after.game.name
                if game in data:
                    data[game] += 1
                else:
                    new = True
                    for g in data:
                        if self.match(g.upper(), after.game.name.upper()) > 0.89:
                            data[g] += 1
                            new = False
                            break
                    if new:
                        data[game] = 1
                dataIO.save_json(filename, data)

    @commands.command(pass_context=True, no_pm=True, name='games')
    async def _games(self, context):
        """Shows top 10 most popular games on this server."""

        server = context.message.server
        filename = 'data/games/{}.json'.format(server.id)
        if dataIO.is_valid_json(filename):
            data = dataIO.load_json(filename)
            games_played = sorted(data, key=lambda x: data[x], reverse=True)
            message = '```Most popular games played on {}\n\n'.format(server.name)
            for i, game in enumerate(games_played, 1):
                if i > 10:
                    break
                message += '{:<5}{:<10}\n'.format(i, game)
            message += '```'
            await self.bot.say(message)


def check_folder():
    if not os.path.exists('data/games'):
        print('Creating data/games folder...')
        os.makedirs('data/games')


def setup(bot):
    check_folder()
    n = Games(bot)
    bot.add_listener(n.listener, 'on_member_update')
    bot.add_cog(n)
