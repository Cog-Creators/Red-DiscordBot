"""Module for Trivia cog."""
from collections import Counter
import yaml
import discord
from discord.ext import commands
from redbot.ext import trivia as ext_trivia
from redbot.core import Config, checks
from redbot.core.data_manager import cog_data_path
from redbot.core.utils.chat_formatting import box, pagify
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
        self.conf = Config.get_conf(self, identifier=UNIQUE_ID, force_registration=True)

        self.conf.register_guild(
            max_score=10,
            timeout=120.0,
            delay=15.0,
            bot_plays=False,
            reveal_answer=True,
            payout_multiplier=0.0,
            allow_override=True,
        )

        self.conf.register_member(wins=0, games=0, total_score=0)

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def triviaset(self, ctx: commands.Context):
        """Manage trivia settings."""
        if ctx.invoked_subcommand is None:
            await ctx.send_help()
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
                lang="py",
            )
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
        await ctx.send("Done. Maximum seconds to answer set to {}." "".format(seconds))

    @triviaset.command(name="stopafter")
    async def triviaset_stopafter(self, ctx: commands.Context, seconds: float):
        """Set how long until trivia stops due to no response."""
        settings = self.conf.guild(ctx.guild)
        if seconds < await settings.delay():
            await ctx.send("Must be larger than the answer time limit.")
            return
        await settings.timeout.set(seconds)
        await ctx.send(
            "Done. Trivia sessions will now time out after {}"
            " seconds of no responses.".format(seconds)
        )

    @triviaset.command(name="override")
    async def triviaset_allowoverride(self, ctx: commands.Context, enabled: bool):
        """Allow/disallow trivia lists to override settings."""
        settings = self.conf.guild(ctx.guild)
        await settings.allow_override.set(enabled)
        enabled = "now" if enabled else "no longer"
        await ctx.send(
            "Done. Trivia lists can {} override the trivia settings"
            " for this server.".format(enabled)
        )

    @triviaset.command(name="botplays")
    async def trivaset_bot_plays(self, ctx: commands.Context, true_or_false: bool):
        """Set whether or not the bot gains points.

        If enabled, the bot will gain a point if no one guesses correctly.
        """
        settings = self.conf.guild(ctx.guild)
        await settings.bot_plays.set(true_or_false)
        await ctx.send(
            "Done. "
            + (
                "I'll gain a point if users don't answer in time."
                if true_or_false
                else "Alright, I won't embarass you at trivia anymore."
            )
        )

    @triviaset.command(name="revealanswer")
    async def trivaset_reveal_answer(self, ctx: commands.Context, true_or_false: bool):
        """Set whether or not the answer is revealed.

        If enabled, the bot will reveal the answer if no one guesses correctly
        in time.
        """
        settings = self.conf.guild(ctx.guild)
        await settings.reveal_answer.set(true_or_false)
        await ctx.send(
            "Done. "
            + (
                "I'll reveal the answer if no one knows it."
                if true_or_false
                else "I won't reveal the answer to the questions anymore."
            )
        )

    @triviaset.command(name="payout")
    @check_global_setting_admin()
    async def triviaset_payout_multiplier(self, ctx: commands.Context, multiplier: float):
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
            await ctx.send("Done. I will no longer reward the winner with a" " payout.")
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
            await ctx.send_help()
            return
        categories = [c.lower() for c in categories]
        session = self._get_trivia_session(ctx.channel)
        if session is not None:
            await ctx.send("There is already an ongoing trivia session in this channel.")
            return
        trivia_dict = {}
        authors = []
        for category in reversed(categories):
            # We reverse the categories so that the first list's config takes
            # priority over the others.
            try:
                dict_ = self.get_trivia_list(category)
            except FileNotFoundError:
                await ctx.send(
                    "Invalid category `{0}`. See `{1}trivia list`"
                    " for a list of trivia categories."
                    "".format(category, ctx.prefix)
                )
            except InvalidListError:
                await ctx.send(
                    "There was an error parsing the trivia list for"
                    " the `{}` category. It may be formatted"
                    " incorrectly.".format(category)
                )
            else:
                trivia_dict.update(dict_)
                authors.append(trivia_dict.pop("AUTHOR", None))
                continue
            return
        if not trivia_dict:
            await ctx.send(
                "The trivia list was parsed successfully, however" " it appears to be empty!"
            )
            return
        settings = await self.conf.guild(ctx.guild).all()
        config = trivia_dict.pop("CONFIG", None)
        if config and settings["allow_override"]:
            settings.update(config)
        settings["lists"] = dict(zip(categories, reversed(authors)))
        session = TriviaSession.start(ctx, trivia_dict, settings)
        self.trivia_sessions.append(session)
        LOG.debug("New trivia session; #%s in %d", ctx.channel, ctx.guild.id)

    @trivia.command(name="stop")
    async def trivia_stop(self, ctx: commands.Context):
        """Stop an ongoing trivia session."""
        session = self._get_trivia_session(ctx.channel)
        if session is None:
            await ctx.send("There is no ongoing trivia session in this channel.")
            return
        author = ctx.author
        auth_checks = (
            await ctx.bot.is_owner(author),
            await ctx.bot.is_mod(author),
            await ctx.bot.is_admin(author),
            author == ctx.guild.owner,
            author == session.ctx.author,
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

        msg = box("**Available trivia lists**\n\n{}" "".format(", ".join(sorted(lists))))
        if len(msg) > 1000:
            await ctx.author.send(msg)
            return
        await ctx.send(msg)

    @trivia.group(name="leaderboard", aliases=["lboard"])
    async def trivia_leaderboard(self, ctx: commands.Context):
        """Leaderboard for trivia.

        Defaults to the top 10 of this server, sorted by total wins. Use
        subcommands for a more customised leaderboard.
        """
        if ctx.invoked_subcommand == self.trivia_leaderboard:
            cmd = self.trivia_leaderboard_server
            if isinstance(ctx.channel, discord.abc.PrivateChannel):
                cmd = self.trivia_leaderboard_global
            await ctx.invoke(cmd, "wins", 10)

    @trivia_leaderboard.command(name="server")
    @commands.guild_only()
    async def trivia_leaderboard_server(
        self, ctx: commands.Context, sort_by: str = "wins", top: int = 10
    ):
        """Leaderboard for this server.

        <sort_by> can be any of the following fields:
         - wins  : total wins
         - avg   : average score
         - total : total correct answers

        <top> is the number of ranks to show on the leaderboard.
        """
        key = self._get_sort_key(sort_by)
        if key is None:
            await ctx.send(
                "Unknown field `{}`, see `{}help trivia "
                "leaderboard server` for valid fields to sort by."
                "".format(sort_by, ctx.prefix)
            )
            return
        guild = ctx.guild
        data = await self.conf.all_members(guild)
        data = {guild.get_member(u): d for u, d in data.items()}
        data.pop(None, None)  # remove any members which aren't in the guild
        await self.send_leaderboard(ctx, data, key, top)

    @trivia_leaderboard.command(name="global")
    async def trivia_leaderboard_global(
        self, ctx: commands.Context, sort_by: str = "wins", top: int = 10
    ):
        """Global trivia leaderboard.

        <sort_by> can be any of the following fields:
         - wins  : total wins
         - avg   : average score
         - total : total correct answers from all sessions
         - games : total games played

        <top> is the number of ranks to show on the leaderboard.
        """
        key = self._get_sort_key(sort_by)
        if key is None:
            await ctx.send(
                "Unknown field `{}`, see `{}help trivia "
                "leaderboard global` for valid fields to sort by."
                "".format(sort_by, ctx.prefix)
            )
            return
        data = await self.conf.all_members()
        collated_data = {}
        for guild_id, guild_data in data.items():
            guild = ctx.bot.get_guild(guild_id)
            if guild is None:
                continue
            for member_id, member_data in guild_data.items():
                member = guild.get_member(member_id)
                if member is None:
                    continue
                collated_member_data = collated_data.get(member, Counter())
                for v_key, value in member_data.items():
                    collated_member_data[v_key] += value
                collated_data[member] = collated_member_data
        await self.send_leaderboard(ctx, collated_data, key, top)

    def _get_sort_key(self, key: str):
        key = key.lower()
        if key in ("wins", "average_score", "total_score", "games"):
            return key
        elif key in ("avg", "average"):
            return "average_score"
        elif key in ("total", "score", "answers", "correct"):
            return "total_score"

    async def send_leaderboard(self, ctx: commands.Context, data: dict, key: str, top: int):
        """Send the leaderboard from the given data.

        Parameters
        ----------
        ctx : commands.Context
            The context to send the leaderboard to.
        data : dict
            The data for the leaderboard. This must map `discord.Member` ->
            `dict`.
        key : str
            The field to sort the data by. Can be ``wins``, ``total_score``,
            ``games`` or ``average_score``.
        top : int
            The number of members to display on the leaderboard.

        Returns
        -------
        `list` of `discord.Message`
            The sent leaderboard messages.

        """
        if not data:
            await ctx.send("There are no scores on record!")
            return
        leaderboard = self._get_leaderboard(data, key, top)
        ret = []
        for page in pagify(leaderboard):
            ret.append(await ctx.send(box(page, lang="py")))
        return ret

    def _get_leaderboard(self, data: dict, key: str, top: int):
        # Mix in average score
        for member, stats in data.items():
            if stats["games"] != 0:
                stats["average_score"] = stats["total_score"] / stats["games"]
            else:
                stats["average_score"] = 0.0
        # Sort by reverse order of priority
        priority = ["average_score", "total_score", "wins", "games"]
        try:
            priority.remove(key)
        except ValueError:
            raise ValueError("{} is not a valid key.".format(key))
        # Put key last in reverse priority
        priority.append(key)
        items = data.items()
        for key in priority:
            items = sorted(items, key=lambda t: t[1][key], reverse=True)
        max_name_len = max(map(lambda m: len(str(m)), data.keys()))
        # Headers
        headers = (
            "Rank",
            "Member{}".format(" " * (max_name_len - 6)),
            "Wins",
            "Games Played",
            "Total Score",
            "Average Score",
        )
        lines = [" | ".join(headers)]
        # Header underlines
        lines.append(" | ".join(("-" * len(h) for h in headers)))
        for rank, tup in enumerate(items, 1):
            member, m_data = tup
            # Align fields to header width
            fields = tuple(
                map(
                    str,
                    (
                        rank,
                        member,
                        m_data["wins"],
                        m_data["games"],
                        m_data["total_score"],
                        round(m_data["average_score"], 2),
                    ),
                )
            )
            padding = [" " * (len(h) - len(f)) for h, f in zip(headers, fields)]
            fields = tuple(f + padding[i] for i, f in enumerate(fields))
            lines.append(" | ".join(fields).format(member=member, **m_data))
            if rank == top:
                break
        return "\n".join(lines)

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
        LOG.debug("Ending trivia session; #%s in %s", channel, channel.guild.id)
        if session in self.trivia_sessions:
            self.trivia_sessions.remove(session)
        if session.scores:
            await self.update_leaderboard(session)

    async def update_leaderboard(self, session):
        """Update the leaderboard with the given scores.

        Parameters
        ----------
        session : TriviaSession
            The trivia session to update scores from.

        """
        max_score = session.settings["max_score"]
        for member, score in session.scores.items():
            if member.id == session.ctx.bot.user.id:
                continue
            stats = await self.conf.member(member).all()
            if score == max_score:
                stats["wins"] += 1
            stats["total_score"] += score
            stats["games"] += 1
            await self.conf.member(member).set(stats)

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
            raise FileNotFoundError("Could not find the `{}` category.".format(category))

        with path.open(encoding="utf-8") as file:
            try:
                dict_ = yaml.load(file)
            except yaml.error.YAMLError as exc:
                raise InvalidListError("YAML parsing failed") from exc
            else:
                return dict_

    def _get_trivia_session(self, channel: discord.TextChannel) -> TriviaSession:
        return next(
            (session for session in self.trivia_sessions if session.ctx.channel == channel), None
        )

    def _all_lists(self):
        personal_lists = tuple(p.resolve() for p in cog_data_path(self).glob("*.yaml"))

        return personal_lists + tuple(ext_trivia.lists())

    def __unload(self):
        for session in self.trivia_sessions:
            session.force_stop()
