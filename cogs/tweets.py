from random import choice as randchoice
from datetime import datetime as dt
from discord.ext import commands
import discord
from .utils.dataIO import dataIO
from .utils import checks
try:
    import tweepy as tw
    twInstalled = True
except:
    twInstalled = False
import os


numbs = {
    "next": "➡",
    "back": "⬅",
    "exit": "❌"
}


class TweetListener(tw.StreamListener):

    def on_status(self, status):
        message = {
            "name": status.user.name,
            "status": status.text,
            "created_at": status.created_at,
            "screen_name": status.user.screen_name,
            "status_id": status.id,
            "retweets": status.retweet_count
        }
        return message


class Tweets():
    """Cog for displaying info from Twitter's API"""
    def __init__(self, bot):
        self.bot = bot
        self.settings_file = 'data/tweets/settings.json'
        settings = dataIO.load_json(self.settings_file)
        if 'consumer_key' in list(settings.keys()):
            self.consumer_key = settings['consumer_key']
        if 'consumer_secret' in list(settings.keys()):
            self.consumer_secret = settings['consumer_secret']
        if 'access_token' in list(settings.keys()):
            self.access_token = settings['access_token']
        if 'access_secret' in list(settings.keys()):
            self.access_secret = settings['access_secret']

    def authenticate(self):
        """Authenticate with Twitter's API"""
        auth = tw.OAuthHandler(self.consumer_key, self.consumer_secret)
        auth.set_access_token(self.access_token, self.access_secret)
        return tw.API(auth)

    async def tweet_menu(self, ctx, post_list: list,
                         message: discord.Message=None,
                         page=0, timeout: int=30):
        """menu control logic for this taken from
           https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py"""
        s = post_list[page]
        colour =\
            ''.join([randchoice('0123456789ABCDEF')
                     for x in range(6)])
        colour = int(colour, 16)
        created_at = s.created_at
        created_at = created_at.strftime("%Y-%m-%d %H:%M:%S")
        post_url =\
            "https://twitter.com/{}/status/{}".format(s.user.screen_name, s.id)
        desc = "Created at: {}".format(created_at)
        em = discord.Embed(title="Tweet by {}".format(s.user.name),
                           colour=discord.Colour(value=colour),
                           url=post_url,
                           description=desc)
        em.add_field(name="Text", value=s.text)
        em.add_field(name="Retweet count", value=str(s.retweet_count))
        if hasattr(s, "extended_entities"):
            em.set_image(url=s.extended_entities["media"][0]["media_url"] + ":thumb")
        if not message:
            message =\
                await self.bot.send_message(ctx.message.channel, embed=em)
            await self.bot.add_reaction(message, "⬅")
            await self.bot.add_reaction(message, "❌")
            await self.bot.add_reaction(message, "➡")
        else:
            message = await self.bot.edit_message(message, embed=em)
        react = await self.bot.wait_for_reaction(
            message=message, user=ctx.message.author, timeout=timeout,
            emoji=["➡", "⬅", "❌"]
        )
        if react is None:
            await self.bot.remove_reaction(message, "⬅", self.bot.user)
            await self.bot.remove_reaction(message, "❌", self.bot.user)
            await self.bot.remove_reaction(message, "➡", self.bot.user)
            return None
        reacts = {v: k for k, v in numbs.items()}
        react = reacts[react.reaction.emoji]
        if react == "next":
            next_page = 0
            if page == len(post_list) - 1:
                next_page = 0  # Loop around to the first item
            else:
                next_page = page + 1
            return await self.tweet_menu(ctx, post_list, message=message,
                                         page=next_page, timeout=timeout)
        elif react == "back":
            next_page = 0
            if page == 0:
                next_page = len(post_list) - 1  # Loop around to the last item
            else:
                next_page = page - 1
            return await self.tweet_menu(ctx, post_list, message=message,
                                         page=next_page, timeout=timeout)
        else:
            return await\
                self.bot.delete_message(message)

    @commands.group(pass_context=True, no_pm=True, name='tweets')
    async def _tweets(self, ctx):
        """Gets various information from Twitter's API"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_tweets.command(pass_context=True, no_pm=True, name='getuser')
    async def get_user(self, ctx, username: str):
        """Get info about the specified user"""
        message = ""
        if username is not None:
            api = self.authenticate()
            user = api.get_user(username)

            colour =\
                ''.join([randchoice('0123456789ABCDEF')
                     for x in range(6)])
            colour = int(colour, 16)
            url = "https://twitter.com/" + user.screen_name
            emb = discord.Embed(title=user.name,
                                colour=discord.Colour(value=colour),
                                url=url,
                                description=user.description)
            emb.set_thumbnail(url=user.profile_image_url)
            emb.add_field(name="Followers", value=user.followers_count)
            emb.add_field(name="Friends", value=user.friends_count)
            if user.verified:
                emb.add_field(name="Verified", value="Yes")
            else:
                emb.add_field(name="Verified", value="No")
            footer = "Created at " + user.created_at.strftime("%Y-%m-%d %H:%M:%S")
            emb.set_footer(text=footer)
            await self.bot.send_message(ctx.message.channel, embed=emb)
        else:
            message = "Uh oh, an error occurred somewhere!"
            await self.bot.say(message)

    @_tweets.command(pass_context=True, no_pm=True, name='gettweets')
    async def get_tweets(self, ctx, username: str, count: int):
        """Gets the specified number of tweets for the specified username"""
        cnt = count
        if count > 25:
            cnt = 25

        if username is not None:
            if cnt < 1:
                await self.bot.say("I can't do that, silly! Please specify a \
                    number greater than or equal to 1")
                return
            msg_list = []
            api = self.authenticate()
            try:
                for status in\
                        tw.Cursor(api.user_timeline, id=username).items(cnt):
                    msg_list.append(status)
            except tw.TweepError as e:
                await self.bot.say("Whoops! Something went wrong here. \
                    The error code is " + str(e))
                return
            await self.tweet_menu(ctx, msg_list, page=0, timeout=30)
        else:
            await self.bot.say("No username specified!")
            return

    @commands.group(pass_context=True, name='tweetset')
    @checks.admin_or_permissions(manage_server=True)
    async def _tweetset(self, ctx):
        """Command for setting required access information for the API"""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_tweetset.group(pass_context=True, hidden=True, name="stream")
    @checks.admin_or_permissions(manage_server=True)
    async def _stream(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_stream.group(pass_context=True, hidden=True, name="term")
    @checks.admin_or_permissions(manage_server=True)
    async def _term(self, ctx):
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @_term.command(pass_context=True, hidden=True, name="add")
    @checks.admin_or_permissions(manage_server=True)
    async def _add(self, ctx, term_to_track):
        if term_to_track is None:
            await self.bot.say("I can't do that, silly!")
        else:
            settings = dataIO.load_json(self.settings_file)
            if ctx.message.server in settings:
                cur_terms = settings["servers"][ctx.message.server]["terms"]
                cur_terms.append(term_to_track)
                settings["servers"][ctx.message.server]["terms"] = cur_terms
            else:
                cur_terms = []
                cur_terms.append(term_to_track)
                settings["servers"] = {}
                settings["servers"][ctx.message.server] = {}
                settings["servers"][ctx.message.server]["terms"] = cur_terms
            dataIO.save_json(self.settings_file, settings)
            await self.bot.say("Added the requested term!")

    @_term.command(pass_context=True, hidden=True, name="remove")
    @checks.admin_or_permissions(manage_server=True)
    async def _remove(self, ctx, term_to_remove):
        settings = dataIO.load_json(self.settings_file)
        if term_to_remove is None:
            await self.bot.say("You didn't specify a term to remove!")
        elif term_to_remove == "all":
            settings["servers"][ctx.message.server]["terms"] = []
            dataIO.save_json(self.settings_file, settings)
            await self.bot.say("Cleared the tracking list!")
        else:
            cur_list = settings["servers"][ctx.message.server]["terms"]
            cur_list.remove(term_to_remove)
            settings["servers"][ctx.message.server]["terms"] = cur_list
            dataIO.save_json(self.settings_file, settings)
            await self.bot.say("Removed the specified term!")

    @_tweetset.command(pass_context=True, name='consumerkey')
    @checks.is_owner()
    async def set_consumer_key(self, ctx, cons_key):
        """Sets the consumer key"""
        message = ""
        if cons_key is not None:
            settings = dataIO.load_json(self.settings_file)
            settings["consumer_key"] = cons_key
            settings = dataIO.save_json(self.settings_file, settings)
            message = "Consumer key saved!"
        else:
            message = "No consumer key provided!"
        await self.bot.say('```{}```'.format(message))

    @_tweetset.command(pass_context=True, name='consumersecret')
    @checks.is_owner()
    async def set_consumer_secret(self, ctx, cons_secret):
        """Sets the consumer secret"""
        message = ""
        if cons_secret is not None:
            settings = dataIO.load_json(self.settings_file)
            settings["consumer_secret"] = cons_secret
            settings = dataIO.save_json(self.settings_file, settings)
            message = "Consumer secret saved!"
        else:
            message = "No consumer secret provided!"
        await self.bot.say('```{}```'.format(message))

    @_tweetset.command(pass_context=True, name='accesstoken')
    @checks.is_owner()
    async def set_access_token(self, ctx, token):
        """Sets the access token"""
        message = ""
        if token is not None:
            settings = dataIO.load_json(self.settings_file)
            settings["access_token"] = token
            settings = dataIO.save_json(self.settings_file, settings)
            message = "Access token saved!"
        else:
            message = "No access token provided!"
        await self.bot.say('```{}```'.format(message))

    @_tweetset.command(pass_context=True, name='accesssecret')
    @checks.is_owner()
    async def set_access_secret(self, ctx, secret):
        """Sets the access secret"""
        message = ""
        if secret is not None:
            settings = dataIO.load_json(self.settings_file)
            settings["access_secret"] = secret
            settings = dataIO.save_json(self.settings_file, settings)
            message = "Access secret saved!"
        else:
            message = "No access secret provided!"
        await self.bot.say('```{}```'.format(message))


def check_folder():
    if not os.path.exists("data/tweets"):
        print("Creating data/tweets folder")
        os.makedirs("data/tweets")


def check_file():
    data = {'consumer_key': '', 'consumer_secret': '',
            'access_token': '', 'access_secret': ''}
    f = "data/tweets/settings.json"
    if not dataIO.is_valid_json(f):
        print("Creating default settings.json...")
        dataIO.save_json(f, data)


def setup(bot):
    check_folder()
    check_file()
    if twInstalled:
        n = Tweets(bot)
        bot.add_cog(n)
    else:
        raise RuntimeError("You need to do 'pip3 install tweepy'")
