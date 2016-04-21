import discord
from discord.ext import commands
from .utils.dataIO import fileIO
import requests
import re
import os
from .utils import checks

class Lastfm:
    """Le Last.fm cog"""
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = "data/lastfm/lastfm.json"
        self.hated_artists = {'coldplay' : 'Coldpoop', 'muse' : 'Unamused'}

    @commands.group(pass_context=True, no_pm=True, aliases=['lf'])
    async def lastfm(self, context):
        """Get Last.fm statistics of a user."""
        pass

    @lastfm.command(pass_context=True, no_pm=True)
    async def last(self, context, *username : str):
        """<username>"""
        settings = fileIO(self.settings_file, "load")
        api_key = settings['LASTFM_API_KEY']
        if api_key != '':
            if not username:
                if context.message.author.id in settings['USERS']:
                    username = settings['USERS'][context.message.author.id]
            else:
                settings['USERS'][context.message.author.id] = username
                fileIO(self.settings_file, "save", settings)

            payload = {'method' : 'user.getRecentTracks', 'api_key' : api_key, 'username' : username, 'limit' : '1', 'format' : 'json'}
            headers = {'user-agent': 'Multivac/1.0.1'}
            r = requests.get('http://ws.audioscrobbler.com/2.0/?', headers=headers, params=payload)
            data = r.json()
            if 'error' in data:
                message = '`{0}`'.format(data['message'])
            else:
                user = data['recenttracks']['@attr']['user']
                artist = data['recenttracks']['track'][0]['artist']['#text']
                x = artist
                if artist.lower() in self.hated_artists:
                    artist = self.hated_artists[artist.lower()]
                song = data['recenttracks']['track'][0]['name']
                payload = {'search_query' : '{0} {1}'.format(x, song)}
                headers = {'user-agent': 'Multivac/1.0.1'}
                r = requests.get('https://www.youtube.com/results?', headers=headers, params=payload)
                search_results = re.findall(r'href=\"\/watch\?v=(.{11})', r.text)
                if len(search_results) > 0:
                    youtube = 'https://www.youtube.com/watch?v={0}\n'.format(search_results[0])
                else: 
                    youtube = ''
                message = 'Last played song by **{0}** is **{1} - {2}**\n{3}'.format(user, artist, song, youtube)
        else:
            message = 'No API key set for Last.fm. Get one at http://www.last.fm/api'
        await self.bot.say(message)

    @lastfm.command(pass_context=True, no_pm=True)
    async def toptracks(self, context, *username : str):
        """<username>"""
        settings = fileIO(self.settings_file, "load")
        api_key = settings['LASTFM_API_KEY']

        if api_key != '':
            if not username:
                if context.message.author.id in settings['USERS']:
                    username = settings['USERS'][context.message.author.id]
            else:
                settings['USERS'][context.message.author.id] = username
                fileIO(self.settings_file, "save", settings)
            payload = {'method' : 'User.getTopTracks', 'api_key' : api_key, 'username' : username, 'limit' : '10', 'format' : 'json'}
            headers = {'user-agent': 'Multivac/1.0.1'}
            r = requests.get('http://ws.audioscrobbler.com/2.0/?', headers=headers, params=payload)
            data = r.json()
            if 'error' in data:
                message = '`{0}`'.format(data['message'])
            else:
                user = data['toptracks']['@attr']['user']
                i = 1
                message = 'Top songs by {0}\n\n'.format(user)
                for track in data['toptracks']['track']:
                    artist = track['artist']['name']
                    if artist.lower() in self.hated_artists:
                        artist = self.hated_artists[artist.lower()]
                    song = track['name']
                    message+= '{0} {1} - {2}\n'.format(str(i).ljust(4), artist, song)
                    i+=1
        else:
            message = 'No API key set for Last.fm. Get one at http://www.last.fm/api'
        await self.bot.say('```{0}```'.format(message))

    @lastfm.command(pass_context=True, no_pm=True)
    async def topartists(self, context, *username : str):
        """<username>"""
        settings = fileIO(self.settings_file, "load")
        api_key = settings['LASTFM_API_KEY']
        if api_key != '':
            if not username:
                if context.message.author.id in settings['USERS']:
                    username = settings['USERS'][context.message.author.id]
            else:
                settings['USERS'][context.message.author.id] = username
                fileIO(self.settings_file, "save", settings)
            payload = {'method' : 'User.getTopArtists', 'api_key' : api_key, 'username' : username, 'limit' : '10', 'format' : 'json'}
            headers = {'user-agent': 'Multivac/1.0.1'}
            r = requests.get('http://ws.audioscrobbler.com/2.0/?', headers=headers, params=payload)
            data = r.json()
            if 'error' in data:
                message = '`{0}`'.format(data['message'])
            else:
                user = data['topartists']['@attr']['user']
                i = 1
                message = 'Top artists by {0}\n\n'.format(user)
                for artist in data['topartists']['artist']:
                    artist_a = artist['name']
                    print(artist_a)
                    if artist_a.lower() in self.hated_artists:
                        artist_a = self.hated_artists[artist_a.lower()]
                    message+= '{0} {1}\n'.format(str(i).ljust(4), artist_a)
                    i+=1
        else:
            message = 'No API key set for Last.fm. Get one at http://www.last.fm/api'
        await self.bot.say('```{0}```'.format(message))

    @lastfm.command(pass_context=True, no_pm=True)
    async def topalbums(self, context, *username : str):
        """<username>"""
        settings = fileIO(self.settings_file, "load")
        api_key = settings['LASTFM_API_KEY']
        if api_key != '':
            if not username:
                if context.message.author.id in settings['USERS']:
                    username = settings['USERS'][context.message.author.id]
            else:
                settings['USERS'][context.message.author.id] = username
                fileIO(self.settings_file, "save", settings)

            payload = {'method' : 'User.getTopAlbums', 'api_key' : api_key, 'username' : username, 'limit' : '10', 'format' : 'json'}
            headers = {'user-agent': 'Multivac/1.0.1'}
            r = requests.get('http://ws.audioscrobbler.com/2.0/?', headers=headers, params=payload)
            data = r.json()
            if 'error' in data:
                message = '`{0}`'.format(data['message'])
            else:
                user = data['topalbums']['@attr']['user']
                i = 1
                message = 'Top albums by {0}\n\n'.format(user)
                for album in data['topalbums']['album']:
                    albums = album['name']
                    artist = album['artist']['name']
                    if artist.lower() in self.hated_artists:
                        artist = self.hated_artists[artist.lower()]
                    message+= '{0} {1} by {2}\n'.format(str(i).ljust(4), albums, artist)
                    i+=1
        else:
            message = 'No API key set for Last.fm. Get one at http://www.last.fm/api'
        await self.bot.say('```{0}```'.format(message))

    @commands.command(name='setlastfmapi', aliases=['setlastfm'], pass_context=True)
    @checks.is_owner()
    async def setlastfmapi(self, context, *arguments : str):
        settings = fileIO(self.settings_file, "load")
        if arguments:
            settings['LASTFM_API_KEY'] = arguments[0]
            fileIO(self.settings_file, "save", settings)

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