from cogs.utils.dataIO import dataIO
from discord.ext import commands
import aiohttp
import discord
import difflib
import os
import re


class Steam:
    def __init__(self, bot):
        self.bot = bot
        self.games = dataIO.load_json('data/steam/games.json')['applist']['apps']['app']

    async def _update_apps(self):
        payload = {}
        url = 'http://api.steampowered.com/ISteamApps/GetAppList/v0001/'
        headers = {'user-agent': 'MARViN-cog/1.0'}
        conn = aiohttp.TCPConnector(verify_ssl=False)
        session = aiohttp.ClientSession(connector=conn)
        async with session.get(url, params=payload, headers=headers) as r:
            data = await r.json()
        session.close()
        self.games = data['applist']['apps']['app']
        dataIO.save_json('data/steam/games.json', data)

    async def _app_info(self, gid):
        url = 'http://store.steampowered.com/api/appdetails?'
        payload = {}
        payload['appids'] = gid
        headers = {'user-agent': 'MARViN-cog/1.0'}
        conn = aiohttp.TCPConnector(verify_ssl=False)
        session = aiohttp.ClientSession(connector=conn)
        async with session.get(url, params=payload, headers=headers) as r:
            data = await r.json()
        session.close()
        if data[str(gid)]['success']:
            data = data[str(gid)]['data']
            info = {}
            info['name'] = data['name']
            info['developers'] = data['developers']
            info['publishers'] = data['publishers']

            if data['is_free']:
                info['price'] = 'Free to Play'
            elif 'price_overview' not in data:
                info['price'] = 'Not available'
            else:
                info['price'] = '{} {}'.format(str(data['price_overview']['final'] / 100), (data['price_overview']['currency']))
                if data['price_overview']['discount_percent'] > 0:
                    info['price'] = '{} {} ({} -{}%)'.format(str(data['price_overview']['final'] / 100), data['price_overview']['currency'], str(data['price_overview']['initial'] / 100), str(data['price_overview']['discount_percent']))
            if data['release_date']['coming_soon']:
                info['release_date'] = 'Coming Soon'
            else:
                info['release_date'] = data['release_date']['date']
            info['genres'] = data['genres']
            info['recommendations'] = ''
            if 'recommendations' in data:
                info['recommendations'] = 'Recommendations: {}\n\n'.format(str(data['recommendations']['total']))
            info['about_the_game'] = re.sub("<.*?>", " ", data['about_the_game'].replace('  ', '').replace('\r', '').replace('<br>', '\n').replace('\t', ''))
            if len(info['about_the_game']) > 500:
                info['about_the_game'] = '{}...'.format(info['about_the_game'][:500-3])
            return info
        return False

    async def _app_type(self, gid):
        url = 'http://store.steampowered.com/api/appdetails?'
        payload = {}
        payload['appids'] = gid
        headers = {'user-agent': 'MARViN-cog/1.0'}
        conn = aiohttp.TCPConnector(verify_ssl=False)
        session = aiohttp.ClientSession(connector=conn)
        async with session.get(url, params=payload, headers=headers) as r:
            data = await r.json()
        session.close()
        if data[str(gid)]['success']:
            data = data[str(gid)]['data']
            app_type = data['type']
            return app_type
        return False

    async def _game_search(self, game):
        games = []
        match = False
        for app in self.games:
            name = app['name']
            appid = app['appid']
            x = difflib.SequenceMatcher(None, name.lower(), game.lower()).ratio()
            if x > 0.92:
                app_type = await self._app_type(appid)
                if app_type == 'game':
                    match = app
            elif game.lower() in name.lower():
                if len(games) > 10:
                    break
                games.append(app)
            if game.lower() == name.lower():
                match = app
                break
        return match, games

    @commands.command(pass_context=True, no_pm=True, name='steam', aliases=['st', 'Steam'])
    async def _steam(self, context, *game: str):
        game = " ".join(game)
        game_match = await self._game_search(game)
        match = game_match[0]
        games = game_match[1]
        if match:
            info = await self._app_info(match['appid'])
            if info:
                em = discord.Embed(title='{}'.format(match['name']), color=discord.Color.blue(), url='http://store.steampowered.com/app/{}'.format(match['appid']))
                em.add_field(name='\a', value='\a', inline=False)
                em.add_field(name='**Price**', value=info['price'])
                em.add_field(name='**Genre**', value=', '.join([genre['description'] for genre in info['genres']]))
                em.add_field(name='\a', value='\a')
                em.add_field(name='**Release date**', value=info['release_date'])
                em.add_field(name='**Developed by**', value=', '.join([developer for developer in info['developers']]))
                em.add_field(name='**Published by**', value=', '.join([publisher for publisher in info['publishers']]))
                em.add_field(name='\a', value=info['about_the_game'], inline=False)
                em.set_footer(text='Information provided by Steam', icon_url='http://store.akamai.steamstatic.com/public/shared/images/header/globalheader_logo.png')
                await self.bot.say(embed=em)
            else:
                message = '`Game was found, but could not retrive information`'
                await self.bot.say(message)
        elif games:
            message = '```This game was not found. But I found close matches:\n\n'
            for game in games:
                message += '{}\n'.format(game['name'])
            message += '```'
            await self.bot.say(message)
        else:
            message = '`This game could not be found`'
            await self.bot.say(message)

    @commands.command(pass_context=True, no_pm=True, name='steamupdate', aliases=['stupdate'])
    async def _update(self, context):
        try:
            await self._update_apps()
            message = 'Game list updated.'
        except Exception as error:
            message = 'Could not update. Check console for more information.'
            print(error)
        await self.bot.say(message)


def check_folder():
    if not os.path.exists('data/steam'):
        print('Creating data/steam folder...')
        os.makedirs('data/steam')


def check_file():
    data = {}
    data['applist'] = {}
    data['applist']['apps'] = {}
    data['applist']['apps']['app'] = []
    f = 'data/steam/games.json'
    if not dataIO.is_valid_json(f):
        print('Creating default games.json...')
        dataIO.save_json(f, data)


def setup(bot):
    check_folder()
    check_file()
    cog = Steam(bot)
    bot.add_cog(cog)
