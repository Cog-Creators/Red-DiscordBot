import datetime
import time
from enum import Enum
from random import randint, choice
from urllib.parse import quote_plus
import aiohttp
import discord
from redbot.core import commands
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.utils.chat_formatting import escape, italics, pagify

_ = Translator("General", __file__)


class RPS(Enum):
    rock = "\N{MOYAI}"
    paper = "\N{PAGE FACING UP}"
    scissors = "\N{BLACK SCISSORS}"


class RPSParser:
    def __init__(self, argument):
        argument = argument.lower()
        if argument == "rock":
            self.choice = RPS.rock
        elif argument == "paper":
            self.choice = RPS.paper
        elif argument == "scissors":
            self.choice = RPS.scissors
        else:
            raise


@cog_i18n(_)
class General:
    """General commands."""

    def __init__(self):
        self.stopwatches = {}
        self.ball = [
            _("As I see it, yes"),
            _("It is certain"),
            _("It is decidedly so"),
            _("Most likely"),
            _("Outlook good"),
            _("Signs point to yes"),
            _("Without a doubt"),
            _("Yes"),
            _("Yes – definitely"),
            _("You may rely on it"),
            _("Reply hazy, try again"),
            _("Ask again later"),
            _("Better not tell you now"),
            _("Cannot predict now"),
            _("Concentrate and ask again"),
            _("Don't count on it"),
            _("My reply is no"),
            _("My sources say no"),
            _("Outlook not so good"),
            _("Very doubtful"),
        ]

    @commands.command()
    async def choose(self, ctx, *choices):
        """Chooses between multiple choices.

        To denote multiple choices, you should use double quotes.
        """
        choices = [escape(c, mass_mentions=True) for c in choices]
        if len(choices) < 2:
            await ctx.send(_("Not enough choices to pick from."))
        else:
            await ctx.send(choice(choices))

    @commands.command()
    async def roll(self, ctx, number: int = 100):
        """Rolls random number (between 1 and user choice)

        Defaults to 100.
        """
        author = ctx.author
        if number > 1:
            n = randint(1, number)
            await ctx.send(_("{} :game_die: {} :game_die:").format(author.mention, n))
        else:
            await ctx.send(_("{} Maybe higher than 1? ;P").format(author.mention))

    @commands.command()
    async def flip(self, ctx, user: discord.Member = None):
        """Flips a coin... or a user.

        Defaults to coin.
        """
        if user != None:
            msg = ""
            if user.id == ctx.bot.user.id:
                user = ctx.author
                msg = _("Nice try. You think this is funny?\n How about *this* instead:\n\n")
            char = "abcdefghijklmnopqrstuvwxyz"
            tran = "ɐqɔpǝɟƃɥᴉɾʞlɯuodbɹsʇnʌʍxʎz"
            table = str.maketrans(char, tran)
            name = user.display_name.translate(table)
            char = char.upper()
            tran = "∀qƆpƎℲפHIſʞ˥WNOԀQᴚS┴∩ΛMX⅄Z"
            table = str.maketrans(char, tran)
            name = name.translate(table)
            await ctx.send(msg + "(╯°□°）╯︵ " + name[::-1])
        else:
            await ctx.send(_("*flips a coin and... ") + choice([_("HEADS!*"), _("TAILS!*")]))

    @commands.command()
    async def rps(self, ctx, your_choice: RPSParser):
        """Play rock paper scissors"""
        author = ctx.author
        player_choice = your_choice.choice
        red_choice = choice((RPS.rock, RPS.paper, RPS.scissors))
        cond = {
            (RPS.rock, RPS.paper): False,
            (RPS.rock, RPS.scissors): True,
            (RPS.paper, RPS.rock): True,
            (RPS.paper, RPS.scissors): False,
            (RPS.scissors, RPS.rock): False,
            (RPS.scissors, RPS.paper): True,
        }

        if red_choice == player_choice:
            outcome = None  # Tie
        else:
            outcome = cond[(player_choice, red_choice)]

        if outcome is True:
            await ctx.send(_("{} You win {}!").format(red_choice.value, author.mention))
        elif outcome is False:
            await ctx.send(_("{} You lose {}!").format(red_choice.value, author.mention))
        else:
            await ctx.send(_("{} We're square {}!").format(red_choice.value, author.mention))

    @commands.command(name="8", aliases=["8ball"])
    async def _8ball(self, ctx, *, question: str):
        """Ask 8 ball a question

        Question must end with a question mark.
        """
        if question.endswith("?") and question != "?":
            await ctx.send("`" + choice(self.ball) + "`")
        else:
            await ctx.send(_("That doesn't look like a question."))

    @commands.command(aliases=["sw"])
    async def stopwatch(self, ctx):
        """Starts/stops stopwatch"""
        author = ctx.author
        if not author.id in self.stopwatches:
            self.stopwatches[author.id] = int(time.perf_counter())
            await ctx.send(author.mention + _(" Stopwatch started!"))
        else:
            tmp = abs(self.stopwatches[author.id] - int(time.perf_counter()))
            tmp = str(datetime.timedelta(seconds=tmp))
            await ctx.send(author.mention + _(" Stopwatch stopped! Time: **") + tmp + "**")
            self.stopwatches.pop(author.id, None)

    @commands.command()
    async def lmgtfy(self, ctx, *, search_terms: str):
        """Creates a lmgtfy link"""
        search_terms = escape(
            search_terms.replace("+", "%2B").replace(" ", "+"), mass_mentions=True
        )
        await ctx.send("https://lmgtfy.com/?q={}".format(search_terms))

    @commands.command(hidden=True)
    @commands.guild_only()
    async def hug(self, ctx, user: discord.Member, intensity: int = 1):
        """Because everyone likes hugs

        Up to 10 intensity levels."""
        name = italics(user.display_name)
        if intensity <= 0:
            msg = "(っ˘̩╭╮˘̩)っ" + name
        elif intensity <= 3:
            msg = "(っ´▽｀)っ" + name
        elif intensity <= 6:
            msg = "╰(*´︶`*)╯" + name
        elif intensity <= 9:
            msg = "(つ≧▽≦)つ" + name
        elif intensity >= 10:
            msg = "(づ￣ ³￣)づ{} ⊂(´・ω・｀⊂)".format(name)
        await ctx.send(msg)

    @commands.command()
    @commands.guild_only()
    async def serverinfo(self, ctx):
        """Shows server's informations"""
        guild = ctx.guild
        online = len([m.status for m in guild.members if m.status != discord.Status.offline])
        total_users = len(guild.members)
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        passed = (ctx.message.created_at - guild.created_at).days
        created_at = _("Since {}. That's over {} days ago!").format(
            guild.created_at.strftime("%d %b %Y %H:%M"), passed
        )

        colour = "".join([choice("0123456789ABCDEF") for x in range(6)])
        colour = randint(0, 0xFFFFFF)

        data = discord.Embed(description=created_at, colour=discord.Colour(value=colour))
        data.add_field(name=_("Region"), value=str(guild.region))
        data.add_field(name=_("Users"), value="{}/{}".format(online, total_users))
        data.add_field(name=_("Text Channels"), value=text_channels)
        data.add_field(name=_("Voice Channels"), value=voice_channels)
        data.add_field(name=_("Roles"), value=len(guild.roles))
        data.add_field(name=_("Owner"), value=str(guild.owner))
        data.set_footer(text=_("Server ID: ") + str(guild.id))

        if guild.icon_url:
            data.set_author(name=guild.name, url=guild.icon_url)
            data.set_thumbnail(url=guild.icon_url)
        else:
            data.set_author(name=guild.name)

        try:
            await ctx.send(embed=data)
        except discord.HTTPException:
            await ctx.send(_("I need the `Embed links` permission to send this."))

    @commands.command()
    async def urban(self, ctx, *, word):
        """Searches urban dictionary entries using the unofficial api"""

        try:
            url = "https://api.urbandictionary.com/v0/define?term=" + str(word).lower()

            headers = {"content-type": "application/json"}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    data = await response.json()

        except:
            await ctx.send(
                _("No Urban dictionary entries were found or there was an error in the process")
            )

        if data.get("error") != 404:

            if await ctx.embed_requested():
                # a list of embeds
                embeds = []
                for ud in data["list"]:
                    embed = discord.Embed()
                    embed.title = _("{} by {}").format(ud["word"].capitalize(), ud["author"])
                    embed.url = ud["permalink"]

                    description = "{} \n \n **Example : ** {}".format(
                        ud["definition"], ud.get("example", "N/A")
                    )
                    if len(description) > 2048:
                        description = "{}...".format(description[:2045])
                    embed.description = description

                    embed.set_footer(
                        text=_("{} Down / {} Up , Powered by urban dictionary").format(
                            ud["thumbs_down"], ud["thumbs_up"]
                        )
                    )
                    embeds.append(embed)

                if embeds is not None and len(embeds) > 0:
                    await menu(
                        ctx,
                        pages=embeds,
                        controls=DEFAULT_CONTROLS,
                        message=None,
                        page=0,
                        timeout=30,
                    )
            else:
                messages = []
                for ud in data["list"]:
                    description = _("{} \n \n **Example : ** {}").format(
                        ud["definition"], ud.get("example", "N/A")
                    )
                    if len(description) > 2048:
                        description = "{}...".format(description[:2045])
                    description = description

                    message = _(
                        "<{}> \n {} by {} \n \n {} \n \n {} Down / {} Up, Powered by urban "
                        "dictionary"
                    ).format(
                        ud["permalink"],
                        ud["word"].capitalize(),
                        ud["author"],
                        description,
                        ud["thumbs_down"],
                        ud["thumbs_up"],
                    )
                    messages.append(message)

                if messages is not None and len(messages) > 0:
                    await menu(
                        ctx,
                        pages=messages,
                        controls=DEFAULT_CONTROLS,
                        message=None,
                        page=0,
                        timeout=30,
                    )
        else:
            await ctx.send(
                _("No Urban dictionary entries were found or there was an error in the process")
            )
            return
