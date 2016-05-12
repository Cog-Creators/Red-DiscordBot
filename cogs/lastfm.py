from discord.ext import commands
from .utils.dataIO import fileIO
import aiohttp
import os
from .utils import checks
from __main__ import send_cmd_help
import datetime


class Lastfm:
    """Le Last.fm cog"""
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = 'data/lastfm/lastfm.json'
        settings = fileIO(self.settings_file, 'load')
        self.api_key = settings['LASTFM_API_KEY']

        self.payload = {}
        self.payload['api_key'] = self.api_key
        self.payload['format'] = 'json'
        self.payload['limit'] = '10'

    @commands.group(pass_context=True, no_pm=True, aliases=['lf'])
    async def lastfm(self, context):
        """Get Last.fm statistics of a user.

Will remember your username after setting one. [p]lastfm last @username will become [p]lastfm last."""
        if context.invoked_subcommand is None:
            await send_cmd_help(context)

    @lastfm.command(pass_context=True, no_pm=True)
    async def set(self, context, *username: str):
        """Set a username"""
        if username:
            try:
                payload = self.payload
                payload['method'] = 'user.getInfo'
                payload['username'] = username[0]
                url = 'http://ws.audioscrobbler.com/2.0/?'
                headers = {'user-agent': 'Red-cog/1.0'}
                conn = aiohttp.TCPConnector(verify_ssl=False)
                session = aiohttp.ClientSession(connector=conn)
                async with session.get(url, params=payload, headers=headers) as r:
                    data = await r.json()
                session.close()
            except Exception as e:
                message = 'Something went terribly wrong! [{}]'.format(e)
            if 'error' in data:
                message = '{}'.format(data['message'])
            else:
                settings = fileIO(self.settings_file, "load")
                settings['USERS'][context.message.author.id] = username[0]
                username = username[0]
                fileIO(self.settings_file, "save", settings)
                message = 'Username set'
        else:
            message = 'Now come on, I need your username!'
        await self.bot.say('```{}```'.format(message))

    @lastfm.command(pass_context=True, no_pm=True)
    async def info(self, context, *username: str):
        """Retrieve general information"""
        if self.api_key != '':
            if not username:
                settings = fileIO(self.settings_file, 'load')
                if context.message.author.id in settings['USERS']:
                    username = settings['USERS'][context.message.author.id]
            else:
                user_patch = username[0].replace('!', '')
                settings = fileIO(self.settings_file, 'load')
                if user_patch[2:-1] in settings['USERS']:
                    username = settings['USERS'][user_patch[2:-1]]
                else:
                    username = user_patch
            try:
                payload = self.payload
                payload['method'] = 'user.getInfo'
                payload['username'] = username
                url = 'http://ws.audioscrobbler.com/2.0/?'
                headers = {'user-agent': 'Red-cog/1.0'}
                conn = aiohttp.TCPConnector(verify_ssl=False)
                session = aiohttp.ClientSession(connector=conn)
                async with session.get(url, params=payload, headers=headers) as r:
                    data = await r.json()
                session.close()
            except Exception as e:
                message = 'Something went terribly wrong! [{}]'.format(e)
            if 'error' in data:
                message = '{}'.format(data['message'])
            else:
                user = data['user']['name']
                playcount = data['user']['playcount']
                registered = data['user']['registered']['unixtime']
                registered = datetime.datetime.fromtimestamp(int(registered)).strftime('%Y-%m-%d %H:%M:%S')
                profile = data['user']['url']
                message = 'Last.fm profile of {}\n\nScrobbles: {}\nRegistered: {}\nProfile: {}'.format(user, playcount, registered, profile)
        else:
            message = 'No API key set for Last.fm. Get one at http://www.last.fm/api'
        await self.bot.say('```{}```'.format(message))

    @lastfm.command(pass_context=True, no_pm=True, aliases=['lp'])
    async def last(self, context, *username: str):
        """Shows the last 10 played songs"""
        if self.api_key != '':
            if not username:
                settings = fileIO(self.settings_file, 'load')
                if context.message.author.id in settings['USERS']:
                    username = settings['USERS'][context.message.author.id]
            else:
                user_patch = username[0].replace('!', '')
                settings = fileIO(self.settings_file, 'load')
                if user_patch[2:-1] in settings['USERS']:
                    username = settings['USERS'][user_patch[2:-1]]
                else:
                    username = user_patch
            try:
                payload = self.payload
                payload['method'] = 'user.getRecentTracks'
                payload['username'] = username
                url = 'http://ws.audioscrobbler.com/2.0/?'
                headers = {'user-agent': 'Red-cog/1.0'}
                conn = aiohttp.TCPConnector(verify_ssl=False)
                session = aiohttp.ClientSession(connector=conn)
                async with session.get(url, params=payload, headers=headers) as r:
                    data = await r.json()
                session.close()
            except Exception as e:
                message = 'Something went terribly wrong! [{}]'.format(e)
            if 'error' in data:
                message = '{}'.format(data['message'])
            else:
                user = data['recenttracks']['@attr']['user']
                message = '```Last 10 songs played by {}\n\n'.format(user)
                for i, track in enumerate(data['recenttracks']['track'], 1):
                    try:
                        if track['@attr']['nowplaying'] == 'true':
                            nowplaying = '(Now playing) '
                    except KeyError:
                        nowplaying = ''
                    artist = track['artist']['#text']
                    song = track['name']
                    # date = track['date']['uts']
                    # date = datetime.datetime.fromtimestamp(int(date)).strftime('%d %b')
                    message += '{} {}{} - {}\n'.format(str(i).ljust(4), nowplaying, artist, song)
                    if i > 9:
                        break
                message += '```'
        else:
            message = 'No API key set for Last.fm. Get one at http://www.last.fm/api'
        await self.bot.say(message)

    @lastfm.command(pass_context=True, no_pm=True, aliases=['tracks', 'ttr'])
    async def toptracks(self, context, *username: str):
        """Top 10 most played songs"""
        if self.api_key != '':
            if not username:
                settings = fileIO(self.settings_file, 'load')
                if context.message.author.id in settings['USERS']:
                    username = settings['USERS'][context.message.author.id]
            else:
                user_patch = username[0].replace('!', '')
                settings = fileIO(self.settings_file, 'load')
                if user_patch[2:-1] in settings['USERS']:
                    username = settings['USERS'][user_patch[2:-1]]
                else:
                    username = user_patch
            try:
                payload = self.payload
                payload['method'] = 'user.getTopTracks'
                payload['username'] = username
                headers = {'user-agent': 'Red-cog/1.0'}
                url = 'http://ws.audioscrobbler.com/2.0/?'
                conn = aiohttp.TCPConnector(verify_ssl=False)
                session = aiohttp.ClientSession(connector=conn)
                async with session.get(url, params=payload, headers=headers) as r:
                    data = await r.json()
                session.close()
            except Exception as e:
                message = 'Something went terribly wrong! [{}]'.format(e)
            if 'error' in data:
                message = '{}'.format(data['message'])
            else:
                user = data['toptracks']['@attr']['user']
                message = 'Top songs played by {0}\n\n'.format(user)
                for i, track in enumerate(data['toptracks']['track'], 1):
                    artist = track['artist']['name']
                    song = track['name']
                    message += '{} {} - {}\n'.format(str(i).ljust(4), artist, song)

        else:
            message = 'No API key set for Last.fm. Get one at http://www.last.fm/api'
        await self.bot.say('```{}```'.format(message))

    @lastfm.command(pass_context=True, no_pm=True, aliases=['artists', 'tar'])
    async def topartists(self, context, *username: str):
        """Top 10 played artists"""
        if self.api_key != '':
            if not username:
                settings = fileIO(self.settings_file, 'load')
                if context.message.author.id in settings['USERS']:
                    username = settings['USERS'][context.message.author.id]
            else:
                user_patch = username[0].replace('!', '')
                settings = fileIO(self.settings_file, 'load')
                if user_patch[2:-1] in settings['USERS']:
                    username = settings['USERS'][user_patch[2:-1]]
                else:
                    username = user_patch
            try:
                payload = self.payload
                payload['method'] = 'user.getTopArtists'
                payload['username'] = username
                headers = {'user-agent': 'Red-cog/1.0'}
                url = 'http://ws.audioscrobbler.com/2.0/?'
                conn = aiohttp.TCPConnector(verify_ssl=False)
                session = aiohttp.ClientSession(connector=conn)
                async with session.get(url, params=payload, headers=headers) as r:
                    data = await r.json()
                session.close()
            except Exception as e:
                message = 'Something went terribly wrong! [{}]'.format(e)

            if 'error' in data:
                message = '{}'.format(data['message'])
            else:
                user = data['topartists']['@attr']['user']
                message = 'Top artists played by {}\n\n'.format(user)
                for i, artist in enumerate(data['topartists']['artist'], 1):
                    artist_a = artist['name']
                    message += '{} {}\n'.format(str(i).ljust(4), artist_a)

        else:
            message = 'No API key set for Last.fm. Get one at http://www.last.fm/api'
        await self.bot.say('```{}```'.format(message))

    @lastfm.command(pass_context=True, no_pm=True, aliases=['albums', 'tab'])
    async def topalbums(self, context, *username: str):
        """Top 10 played albums"""
        if self.api_key != '':
            if not username:
                settings = fileIO(self.settings_file, 'load')
                if context.message.author.id in settings['USERS']:
                    username = settings['USERS'][context.message.author.id]
            else:
                user_patch = username[0].replace('!', '')
                settings = fileIO(self.settings_file, 'load')
                if user_patch[2:-1] in settings['USERS']:
                    username = settings['USERS'][user_patch[2:-1]]
                else:
                    username = user_patch
            try:
                payload = self.payload
                payload['method'] = 'user.getTopAlbums'
                payload['username'] = username
                headers = {'user-agent': 'Red-cog/1.0'}
                url = 'http://ws.audioscrobbler.com/2.0/?'
                conn = aiohttp.TCPConnector(verify_ssl=False)
                session = aiohttp.ClientSession(connector=conn)
                async with session.get(url, params=payload, headers=headers) as r:
                    data = await r.json()
                    print('ayy')
                session.close()
            except Exception as e:
                message = 'Something went terribly wrong! [{}]'.format(e)
            if 'error' in data:
                message = '{}'.format(data['message'])
            else:
                user = data['topalbums']['@attr']['user']
                message = 'Top albums played by {0}\n\n'.format(user)
                for i, album in enumerate(data['topalbums']['album'], 1):
                    albums = album['name']
                    artist = album['artist']['name']
                    message += '{} {} by {}\n'.format(str(i).ljust(4), albums, artist)
        else:
            message = 'No API key set. Get one at http://www.last.fm/api'
        await self.bot.say('```{}```'.format(message))

    @lastfm.command(pass_context=True)
    @checks.is_owner()
    async def apikey(self, context, *key: str):
        """Sets the Last.fm API key - for bot owner only."""
        settings = fileIO(self.settings_file, "load")
        if key:
            settings['LASTFM_API_KEY'] = key[0]
            fileIO(self.settings_file, "save", settings)
            await self.bot.say('```Done```')


def check_folder():
    if not os.path.exists("data/lastfm"):
        print("Creating data/lastfm folder...")
        os.makedirs("data/lastfm")


def check_file():
    data = {}
    data['LASTFM_API_KEY'] = ''
    data['USERS'] = {}
    f = "data/lastfm/lastfm.json"
    if not fileIO(f, "check"):
        print("Creating default lastfm.json...")
        fileIO(f, "save", data)


def setup(bot):
    check_folder()
    check_file()
    n = Lastfm(bot)
    bot.add_cog(n)
