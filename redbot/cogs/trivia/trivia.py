"""Module for Trivia cog."""
import yaml
import discord
from discord.ext import commands
import redbot.trivia
from redbot.core import Config, checks
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.chat_formatting import box
from redbot.cogs.bank import check_global_setting_admin
from .log import LOG
from .session import TriviaSession

__all__ = ["Trivia", "UNIQUE_ID"]

UNIQUE_ID = 0xb3c0e453


class InvalidListError(Exception):
    """A Trivia list file is in invalid format."""
    pass


class Trivia:
    """Play trivia with friends!"""

    def __init__(self):
        self.trivia_sessions = []
        self.conf = Config.get_conf(
            self, identifier=UNIQUE_ID, force_registration=True)

        self.conf.register_guild(
            max_score=10,
            timeout=120.0,
            delay=15.0,
            bot_plays=False,
            reveal_answer=True,
            payout_multiplier=0.0,
            allow_override=True)

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def triviaset(self, ctx: commands.Context):
        """Manage trivia settings."""
        if ctx.invoked_subcommand is None:
            await ctx.bot.send_cmd_help(ctx)
            settings = self.conf.guild(ctx.guild)
            settings_dict = await settings.all()
            msg = box(
                "**Current settings**\n"
                "Bot gains points: {bot_plays}\n"
                "Answer time limit: {delay} seconds\n"
                "Lack of response timeout: {timeout} seconds\n"
                "Points to win: {max_score}\n"
                "Reveal answer on timeout: {reveal_answer}\n"
                "Payout multiplier: {payout_multiplier}\n"
                "Allow lists to override settings: {allow_override}"
                "".format(**settings_dict),
                lang="py")
            await ctx.send(msg)

    @triviaset.command(name="maxscore")
    async def triviaset_max_score(self, ctx: commands.Context, score: int):
        """Set the total points required to win."""
        if score < 0:
            await ctx.send("Score must be greater than 0.")
            return
        settings = self.conf.guild(ctx.guild)
        await settings.max_score.set(score)
        await ctx.send("Done. Points required to win set to {}.".format(score))

    @triviaset.command(name="timelimit")
    async def triviaset_timelimit(self, ctx: commands.Context, seconds: float):
        """Set the maximum seconds permitted to answer a question."""
        if seconds < 4.0:
            await ctx.send("Must be at least 4 seconds.")
            return
        settings = self.conf.guild(ctx.guild)
        await settings.delay.set(seconds)
        await ctx.send("Done. Maximum seconds to answer set to {}."
                       "".format(seconds))

    @triviaset.command(name="stopafter")
    async def triviaset_stopafter(self, ctx: commands.Context, seconds: float):
        """Set how long until trivia stops due to no response."""
        settings = self.conf.guild(ctx.guild)
        if seconds < await settings.delay():
            await ctx.send("Must be larger than the answer time limit.")
            return
        await settings.timeout.set(seconds)
        await ctx.send("Done. Trivia sessions will now time out after {}"
                       " seconds of no responses.".format(seconds))

    @triviaset.command(name="override")
    async def triviaset_allowoverride(self, ctx: commands.Context, enabled: bool):
        """Allow/disallow trivia lists to override settings."""
        settings = self.conf.guild(ctx.guild)
        await settings.allow_override.set(enabled)
        enabled = "now" if enabled else "no longer"
        await ctx.send("Done. Trivia lists can {} override the trivia settings"
                       " for this server.".format(enabled))

    @triviaset.command(name="botplays")
    async def trivaset_bot_plays(self,
                                 ctx: commands.Context,
                                 true_or_false: bool):
        """Set whether or not the bot gains points.

        If enabled, the bot will gain a point if no one guesses correctly.
        """
        settings = self.conf.guild(ctx.guild)
        await settings.bot_plays.set(true_or_false)
        await ctx.send("Done. " + (
            "I'll gain a point if users don't answer in time." if true_or_false
            else "Alright, I won't embarass you at trivia anymore."))

    @triviaset.command(name="revealanswer")
    async def trivaset_reveal_answer(self,
                                     ctx: commands.Context,
                                     true_or_false: bool):
        """Set whether or not the answer is revealed.

        If enabled, the bot will reveal the answer if no one guesses correctly
        in time.
        """
        settings = self.conf.guild(ctx.guild)
        await settings.reveal_answer.set(true_or_false)
        await ctx.send("Done. " + (
            "I'll reveal the answer if no one knows it." if true_or_false else
            "I won't reveal the answer to the questions anymore."))

    @triviaset.command(name="payout")
    @check_global_setting_admin()
    async def triviaset_payout_multiplier(self,
                                          ctx: commands.Context,
                                          multiplier: float):
        """Set the payout multiplier.

        This can be any positive decimal number. If a user wins trivia when at
        least 3 members are playing, they will receive credits. Set to 0 to
        disable.

        The number of credits is determined by multiplying their total score by
        this multiplier.
        """
        settings = self.conf.guild(ctx.guild)
        if multiplier < 0:
            await ctx.send("Multiplier must be at least 0.")
            return
        await settings.payout_multiplier.set(multiplier)
        if not multiplier:
            await ctx.send("Done. I will no longer reward the winner with a"
                           " payout.")
            return
        await ctx.send("Done. Payout multiplier set to {}.".format(multiplier))

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def trivia(self, ctx: commands.Context, *categories: str):
        """Start trivia session on the specified category.

        You may list multiple categories, in which case the trivia will involve
        questions from all of them.
        """
        if not categories:
            await ctx.bot.send_cmd_help(ctx)
            return
        categories = [c.lower() for c in categories]
        session = self._get_trivia_session(ctx.channel)
        if session is not None:
            await ctx.send(
                "There is already an ongoing trivia session in this channel.")
            return
        trivia_dict = {}
        for category in reversed(categories):
            # We reverse the categories so that the first list's config takes
            # priority over the others.
            try:
                dict_ = self.get_trivia_list(category)
            except FileNotFoundError:
                await ctx.send("Invalid category `{0}`. See `{1}trivia list`"
                               " for a list of trivia categories."
                               "".format(category, ctx.prefix))
            except InvalidListError:
                await ctx.send("There was an error parsing the trivia list for"
                               " the `{}` category. It may be formatted"
                               " incorrectly.".format(category))
            else:
                trivia_dict.update(dict_)
                continue
            return
        if not trivia_dict:
            await ctx.send("The trivia list was parsed successfully, however"
                           " it appears to be empty!")
            return
        settings = await self.conf.guild(ctx.guild).all()
        config = trivia_dict.pop("CONFIG", None)
        if config and settings["allow_override"]:
            settings.update(config)
        session = TriviaSession.start(ctx, trivia_dict, settings)
        self.trivia_sessions.append(session)
        LOG.debug("New trivia session; #%s in %d", ctx.channel, ctx.guild.id)

    @trivia.command(name="stop")
    async def trivia_stop(self, ctx: commands.Context):
        """Stop an ongoing trivia session."""
        session = self._get_trivia_session(ctx.channel)
        if session is None:
            await ctx.send(
                "There is no ongoing trivia session in this channel.")
            return
        author = ctx.author
        auth_checks = (
            await ctx.bot.is_owner(author),
            await ctx.bot.is_mod(author),
            await ctx.bot.is_admin(author),
            author == ctx.guild.owner,
            author == session.ctx.author
        )
        if any(auth_checks):
            await session.end_game()
            session.force_stop()
            await ctx.send("Trivia stopped.")
        else:
            await ctx.send("You are not allowed to do that.")

    @trivia.command(name="list")
    async def trivia_list(self, ctx: commands.Context):
        """List available trivia categories."""
        lists = set(p.stem for p in self._all_lists())

        msg = box("**Available trivia lists**\n\n{}"
                  "".format(", ".join(sorted(lists))))
        if len(msg) > 1000:
            await ctx.author.send(msg)
            return
        await ctx.send(msg)

    async def on_trivia_end(self, session: TriviaSession):
        """Event for a trivia session ending.

        This method removes the session from this cog's sessions, and
        cancels any tasks which it was running.

        Parameters
        ----------
        session : TriviaSession
            The session which has just ended.

        """
        channel = session.ctx.channel
        LOG.debug("Ending trivia session; #%s in %s", channel,
                  channel.guild.id)
        if session in self.trivia_sessions:
            self.trivia_sessions.remove(session)

    def get_trivia_list(self, category: str) -> dict:
        """Get the trivia list corresponding to the given category.

        Parameters
        ----------
        category : str
            The desired category. Case sensitive.

        Returns
        -------
        `dict`
            A dict mapping questions (`str`) to answers (`list` of `str`).

        """
        try:
            path = next(p for p in self._all_lists() if p.stem == category)
        except StopIteration:
            raise FileNotFoundError("Could not find the `{}` category"
                                    "".format(category))

        with path.open() as file:
            try:
                dict_ = yaml.load(file)
            except yaml.error.YAMLError as exc:
                raise InvalidListError("YAML parsing failed") from exc
            else:
                return dict_

    def _get_trivia_session(self,
                            channel: discord.TextChannel) -> TriviaSession:
        return next((session for session in self.trivia_sessions
                     if session.ctx.channel == channel), None)

    def _all_lists(self):
        personal_lists = tuple(p.resolve()
                               for p in cog_data_path(self).glob("*.yaml"))

        return personal_lists + tuple(redbot.trivia.lists())

    def __unload(self):
        for session in self.trivia_sessions:
            session.force_stop()
