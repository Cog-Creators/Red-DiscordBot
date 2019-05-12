import datetime
import time
from enum import Enum
from random import randint, choice
import aiohttp
import discord
from redbot.core import commands
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.menus import menu, DEFAULT_CONTROLS
from redbot.core.utils.chat_formatting import escape, italics

_ = T_ = Translator("General", __file__)


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
            self.choice = None


@cog_i18n(_)
class General(commands.Cog):
    """General commands."""

    global _
    _ = lambda s: s
    ball = [
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
    _ = T_

    def __init__(self):
        super().__init__()
        self.stopwatches = {}

    @commands.command()
    async def choose(self, ctx, *choices):
        """Choose between multiple options.

        To denote options which include whitespace, you should use
        double quotes.
        """
        choices = [escape(c, mass_mentions=True) for c in choices]
        if len(choices) < 2:
            await ctx.send(_("Not enough options to pick from."))
        else:
            await ctx.send(choice(choices))

    @commands.command()
    async def roll(self, ctx, number: int = 100):
        """Roll a random number.

        The result will be between 1 and `<number>`.

        `<number>` defaults to 100.
        """
        author = ctx.author
        if number > 1:
            n = randint(1, number)
            await ctx.send("{author.mention} :game_die: {n} :game_die:".format(author=author, n=n))
        else:
            await ctx.send(_("{author.mention} Maybe higher than 1? ;P").format(author=author))

    @commands.command()
    async def flip(self, ctx, user: discord.Member = None):
        """Flip a coin... or a user.

        Defaults to a coin.
        """
        if user is not None:
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
        """Play Rock Paper Scissors."""
        author = ctx.author
        player_choice = your_choice.choice
        if not player_choice:
            return await ctx.send("This isn't a valid option. Try rock, paper, or scissors.")
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
            await ctx.send(
                _("{choice} You win {author.mention}!").format(
                    choice=red_choice.value, author=author
                )
            )
        elif outcome is False:
            await ctx.send(
                _("{choice} You lose {author.mention}!").format(
                    choice=red_choice.value, author=author
                )
            )
        else:
            await ctx.send(
                _("{choice} We're square {author.mention}!").format(
                    choice=red_choice.value, author=author
                )
            )

    @commands.command(name="8", aliases=["8ball"])
    async def _8ball(self, ctx, *, question: str):
        """Ask 8 ball a question.

        Question must end with a question mark.
        """
        if question.endswith("?") and question != "?":
            await ctx.send("`" + T_(choice(self.ball)) + "`")
        else:
            await ctx.send(_("That doesn't look like a question."))

    @commands.command(aliases=["sw"])
    async def stopwatch(self, ctx):
        """Start or stop the stopwatch."""
        author = ctx.author
        if author.id not in self.stopwatches:
            self.stopwatches[author.id] = int(time.perf_counter())
            await ctx.send(author.mention + _(" Stopwatch started!"))
        else:
            tmp = abs(self.stopwatches[author.id] - int(time.perf_counter()))
            tmp = str(datetime.timedelta(seconds=tmp))
            await ctx.send(
                author.mention + _(" Stopwatch stopped! Time: **{seconds}**").format(seconds=tmp)
            )
            self.stopwatches.pop(author.id, None)

    @commands.command()
    async def lmgtfy(self, ctx, *, search_terms: str):
        """Create a lmgtfy link."""
        search_terms = escape(
            search_terms.replace("+", "%2B").replace(" ", "+"), mass_mentions=True
        )
        await ctx.send("https://lmgtfy.com/?q={}".format(search_terms))

    @commands.command(hidden=True)
    @commands.guild_only()
    async def hug(self, ctx, user: discord.Member, intensity: int = 1):
        """Because everyone likes hugs!

        Up to 10 intensity levels.
        """
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
        else:
            # For the purposes of "msg might not be defined" linter errors
            raise RuntimeError
        await ctx.send(msg)

    @commands.command()
    @commands.guild_only()
    async def serverinfo(self, ctx, details: bool = False):
        """
            Show server information.
        
            `details`: Toggle it to `True` to show more
            information about this server.
            Defaults to False.
        """
        guild = ctx.guild

        def check_feature(feature):
            return "\N{WHITE HEAVY CHECK MARK}" if feature in guild.features else "\N{CROSS MARK}"

        format_kwargs = {
            "vip": check_feature("VIP_REGIONS"),
            "van": check_feature("VANITY_URL"),
            "splash": check_feature("INVITE_SPLASH"),
            "m_emojis": check_feature("MORE_EMOJI"),
            "verify": check_feature("VERIFIED"),
        }

        verif = {
            0: _("0 - None"),
            1: _("1 - Low"),
            2: _("2 - Medium"),
            3: _("3 - Hard"),
            4: _("4 - Extreme"),
        }
        region = {
            "vip-us-east": _("__VIP__ US East :flag_us:"),
            "vip-us-west": _("__VIP__ US West :flag_us:"),
            "vip-amsterdam": _("__VIP__ Amsterdam :flag_nl:"),
            "eu-west": _("EU West :flag_eu:"),
            "eu-central": _("EU Central :flag_eu:"),
            "london": _("London :flag_gb:"),
            "frankfurt": _("Frankfurt :flag_de:"),
            "amsterdam": _("Amsterdam :flag_nl:"),
            "us-west": _("US West :flag_us:"),
            "us-east": _("US East :flag_us:"),
            "us-south": _("US South :flag_us:"),
            "us-central": _("US Central :flag_us:"),
            "singapore": _("Singapore :flag_sg:"),
            "sydney": _("Sydney :flag_au:"),
            "brazil": _("Brazil :flag_br:"),
            "hongkong": _("Hong Kong :flag_hk:"),
            "russia": _("Russia :flag_ru:"),
            "japan": _("Japan :flag_jp:"),
            "southafrica": _("South Africa :flag_za:"),
            "india": _("India :flag_in:"),
        }

        online = len([m.status for m in guild.members if m.status == discord.Status.online])
        idle = len([m.status for m in guild.members if m.status == discord.Status.idle])
        dnd = len([m.status for m in guild.members if m.status == discord.Status.dnd])
        offline = len([m.status for m in guild.members if m.status == discord.Status.offline])
        streaming = len([m for m in guild.members if isinstance(m.activity, discord.Streaming)])
        mobile = len([m for m in guild.members if m.is_on_mobile()])
        lurkers = len([m for m in guild.members if m.joined_at is None])
        total_users = len(guild.members)
        humans = len([a for a in ctx.guild.members if a.bot == False])
        bots = len([a for a in ctx.guild.members if a.bot])
        text_channels = len(guild.text_channels)
        voice_channels = len(guild.voice_channels)
        passed = (ctx.message.created_at - guild.created_at).days
        created_at = _("Created on **{date}**. That's over **{num}** days ago !").format(
            date=guild.created_at.strftime("%d %b %Y %H:%M"), num=passed
        )
        joined_at = guild.me.joined_at
        since_joined = (ctx.message.created_at - joined_at).days
        bot_joined = joined_at.strftime("%d %b %Y %H:%M:%S")
        joined_on = _(
            "{bot_name} joined this server on {bot_join}. That's over {since_join} days ago !"
        ).format(bot_name=ctx.bot.user.name, bot_join=bot_joined, since_join=since_joined)
        data = discord.Embed(description=created_at, colour=(await ctx.embed_colour()))
        if details:
            data.add_field(
                name=_("Members:"),
                value=_(
                    "Total users: **{total}**\n{lurkers}Humans: **{hum}** • Bots: **{bots}**\n"
                    "📗 `{online}` 📙 `{idle}`\n📕 `{dnd}` 📓 `{off}`\n"
                    "🎥 `{streaming}` 📱 `{mobile}`\n"
                ).format(
                    total=total_users,
                    lurkers=_("Lurkers: **{}**\n").format(lurkers) if lurkers else "",
                    hum=humans,
                    bots=bots,
                    online=online,
                    idle=idle,
                    dnd=dnd,
                    off=offline,
                    streaming=streaming,
                    mobile=mobile,
                ),
            )
            data.add_field(
                name=_("Channels:"),
                value=_("💬 Text: **{text}**\n🔊 Voice: **{voice}**").format(
                    text=text_channels, voice=voice_channels
                ),
            )
            data.add_field(
                name=_("Utility:"),
                value=_(
                    "Owner: **{owner}**\nRegion: **{region}**\nVerif. level: **{verif}**\nServer ID: **{id}**"
                ).format(
                    owner=guild.owner,
                    region=region[str(guild.region)],
                    verif=verif[int(guild.verification_level)],
                    id=guild.id,
                ),
            )
            data.add_field(
                name=_("Misc:"),
                value=_(
                    "AFK channel: **{afk_chan}**\nAFK Timeout: **{afk_timeout}sec**\nCustom emojis: **{emojis}**\nRoles: **{roles}**"
                ).format(
                    afk_chan=guild.afk_channel,
                    afk_timeout=guild.afk_timeout,
                    emojis=len(guild.emojis),
                    roles=len(guild.roles),
                ),
            )
            if guild.features:
                data.add_field(
                    name=_("Special features:"),
                    value=_(
                        "{vip} VIP Regions\n{van} Vanity URL\n{splash} Splash Invite\n{m_emojis} More Emojis\n{verify} Verified"
                    ).format(**format_kwargs),
                )
            data.set_author(name=guild.name)
            if "VERIFIED" in guild.features:
                data.set_author(
                    name=guild.name,
                    icon_url="https://cdn.discordapp.com/emojis/457879292152381443.png",
                )
            if guild.icon_url:
                data.set_thumbnail(url=guild.icon_url)
            else:
                data.set_thumbnail(
                    url="https://cdn.discordapp.com/attachments/494975386334134273/529843761635786754/Discord-Logo-Black.png"
                )
            data.set_footer(text=joined_on)

        else:
            data = discord.Embed(description=created_at, colour=(await ctx.embed_colour()))
            data.add_field(name=_("Region"), value=region[str(guild.region)])
            data.add_field(name=_("Users"), value=f"{online}/{total_users}")
            data.add_field(name=_("Text Channels"), value=str(text_channels))
            data.add_field(name=_("Voice Channels"), value=str(voice_channels))
            data.add_field(name=_("Roles"), value=str(len(guild.roles)))
            data.add_field(name=_("Owner"), value=str(guild.owner))
            data.set_footer(text=_("Server ID: ") + str(guild.id))

            if guild.icon_url:
                data.set_author(name=guild.name, url=guild.icon_url)
                data.set_thumbnail(url=guild.icon_url)
            else:
                data.set_author(name=guild.name)

        try:
            await ctx.send(embed=data)
        except discord.Forbidden:
            await ctx.send(_("I need the `Embed links` permission to send this."))

    @commands.command()
    async def urban(self, ctx, *, word):
        """Search the Urban Dictionary.

        This uses the unofficial Urban Dictionary API.
        """

        try:
            url = "https://api.urbandictionary.com/v0/define?term=" + str(word).lower()

            headers = {"content-type": "application/json"}

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    data = await response.json()

        except aiohttp.ClientError:
            await ctx.send(
                _("No Urban Dictionary entries were found, or there was an error in the process.")
            )
            return

        if data.get("error") != 404:
            if not data["list"]:
                return await ctx.send(_("No Urban Dictionary entries were found."))
            if await ctx.embed_requested():
                # a list of embeds
                embeds = []
                for ud in data["list"]:
                    embed = discord.Embed()
                    embed.title = _("{word} by {author}").format(
                        word=ud["word"].capitalize(), author=ud["author"]
                    )
                    embed.url = ud["permalink"]

                    description = _("{definition}\n\n**Example:** {example}").format(**ud)
                    if len(description) > 2048:
                        description = "{}...".format(description[:2045])
                    embed.description = description

                    embed.set_footer(
                        text=_(
                            "{thumbs_down} Down / {thumbs_up} Up, Powered by Urban Dictionary."
                        ).format(**ud)
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
                    ud.setdefault("example", "N/A")
                    description = _("{definition}\n\n**Example:** {example}").format(**ud)
                    if len(description) > 2048:
                        description = "{}...".format(description[:2045])

                    message = _(
                        "<{permalink}>\n {word} by {author}\n\n{description}\n\n"
                        "{thumbs_down} Down / {thumbs_up} Up, Powered by Urban Dictionary."
                    ).format(word=ud.pop("word").capitalize(), description=description, **ud)
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
                _("No Urban Dictionary entries were found, or there was an error in the process.")
            )
