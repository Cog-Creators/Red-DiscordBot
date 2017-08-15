"""Module for Trivia cog."""
from typing import List
import pathlib
import chardet
import discord
from discord.ext import commands
from core import Config, checks
from core.bot import Red
from core.utils.chat_formatting import box
from .log import LOG
from .session import TriviaSession

UNIQUE_ID = 0xb3c0e453

def parse_trivia_list(path: str) -> List[tuple]:
    """Parse the trivia list file at the given file path."""
    ret = []
    with open(path, "rb") as file_:
        try:
            encoding = chardet.detect(file_.read())["encoding"]
        except (KeyError, TypeError):
            encoding = "ISO-8859-1"

    with open(path, "r", encoding=encoding) as file_:
        trivia_list = file_.readlines()

    for line in trivia_list:
        if "`" not in line:
            continue
        line = line.replace("\n", "")
        line = line.split("`")
        question = line[0]
        answers = []
        for ans in line[1:]:
            answers.append(ans.strip())
        if len(line) >= 2 and question and answers:
            ret.append((question, answers))

    if not ret:
        raise ValueError("Empty trivia list")

    return ret

class Trivia:
    """Play trivia with friends!"""

    def __init__(self, bot: Red):
        self.bot = bot
        self.trivia_sessions = []
        self.lists_dir = "cogs/trivia/lists" # Temporary solution
        self.conf = Config.get_conf(self,
                                    identifier=UNIQUE_ID,
                                    force_registration=True)

        self.conf.register_guild(
            max_score=10,
            timeout=120,
            delay=15,
            bot_plays=False,
            reveal_answer=True
        )

    @commands.group()
    @commands.guild_only()
    @checks.mod_or_permissions(administrator=True)
    async def triviaset(self, ctx: commands.Context):
        """Manage trivia settings."""
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)
            settings = self.conf.guild(ctx.guild)
            settings_dict = await settings.all()
            msg = box("**Current settings**\n"
                      "Red gains points: {bot_plays}\n"
                      "Seconds to answer: {delay}\n"
                      "Points to win: {max_score}\n"
                      "Reveal answer on timeout: {reveal_answer}\n"
                      "".format(**settings_dict), lang="py")
            await ctx.send(msg)

    @triviaset.command(name="maxscore")
    async def triviaset_max_score(self, ctx: commands.Context, score: int):
        """Points required to win."""
        if score < 0:
            await ctx.send("Score must be greater than 0.")
            return
        settings = self.conf.guild(ctx.guild)
        await settings.max_score.set(score)
        await ctx.send("Points required to win set to {}.".format(score))

    @triviaset.command(name="timelimit")
    async def triviaset_delay(self, ctx: commands.Context, seconds: int):
        """Maximum seconds to answer a question."""
        if seconds < 4:
            await ctx.send("Must be greater than 4 seconds.")
            return
        settings = self.conf.guild(ctx.guild)
        await settings.delay.set(seconds)
        await ctx.send("Maximum seconds to answer set to {}.".format(seconds))

    @triviaset.command(name="botplays")
    async def trivaset_bot_plays(self, ctx: commands.Context):
        """Red gains points.

        This is a toggle. If enabled, Red will gain a point if
         no one guesses correctly.
        """
        settings = self.conf.guild(ctx.guild)
        enabled = not await settings.bot_plays()
        await settings.bot_plays.set(enabled)
        await ctx.send("I'll gain a point everytime you don't answer in time."
                       if enabled else
                       "Alright, I won't embarass you at trivia anymore.")

    @triviaset.command(name="revealanswer")
    async def trivaset_reveal_answer(self, ctx: commands.Context):
        """Reveals answer to question on timeout.

        This is a toggle. If enabled, Red will reveal the answer if no
         one guesses correctly.
        """
        settings = self.conf.guild(ctx.guild)
        enabled = not await settings.reveal_answer()
        await settings.reveal_answer.set(enabled)
        await ctx.send("I'll reveal the answer if no one knows it."
                       if enabled else
                       "I won't reveal the answer to the questions anymore.")

    @commands.group(invoke_without_command=True)
    @commands.guild_only()
    async def trivia(self, ctx: commands.Context, category: str):
        """Start trivia session on the specified category."""
        category = category.lower()
        session = self._get_trivia_session(ctx.channel)
        if session is not None:
            await ctx.send("There is already an ongoing trivia session in this channel.")
            return
        if not self._category_exists(category):
            await ctx.send("Invalid category. See `{}trivia list` for a list of trivia"
                           " categories.".format(ctx.prefix))
            return
        trivia_list = self.get_trivia_list(category)
        settings = self.conf.guild(ctx.guild)
        session = TriviaSession(ctx, trivia_list, settings)
        self.trivia_sessions.append(session)
        LOG.debug("New trivia session; #%s in %s", ctx.channel, ctx.guild)
        await session.run()

    @trivia.command(name="stop")
    async def trivia_stop(self, ctx: commands.Context):
        """Stops an ongoing trivia session."""
        session = self._get_trivia_session(ctx.channel)
        if session is None:
            await ctx.send("There's no ongoing trivia session in this channel.")
            return
        author = ctx.author
        is_owner = await ctx.bot.is_owner(ctx.author)
        mod_role_id = await ctx.bot.db.guild(ctx.guild).mod_role()
        admin_role_id = await ctx.bot.db.guild(ctx.guild).admin_role()

        mod_role = discord.utils.get(ctx.guild.roles, id=mod_role_id)
        admin_role = discord.utils.get(ctx.guild.roles, id=admin_role_id)

        is_staff = mod_role in author.roles or admin_role in author.roles
        is_guild_owner = author == ctx.guild.owner
        is_authorized = is_staff or is_owner or is_guild_owner
        if author == session.ctx.author or is_authorized:
            await session.end_game()
            await ctx.send("Trivia stopped.")
        else:
            await ctx.send("You are not allowed to do that.")

    @trivia.command(name="list")
    async def trivia_list(self, ctx: commands.Context):
        """Lists available trivia categories."""
        path = self._get_lists_path()
        if path is None:
            await ctx.send("There are no trivia lists available.")
            return
        filenames = [p.name for p in path.iterdir()]
        lists = [l.replace(".txt", "") for l in filenames
                 if l.endswith(".txt") and " " not in l]
        del filenames
        if not lists:
            await ctx.send("There are no trivia lists available.")
            return
        msg = box("**Available trivia lists**\n\n{}"
                  "".format(", ".join(sorted(lists)), lang="diff"))
        if len(lists) > 100:
            await ctx.author.send(msg)
            return
        await ctx.send(msg)

    async def end_session(self, session: TriviaSession):
        """Fires when a trivia session ends, and
         removes it from this cog's sessions.
        """
        channel = session.ctx.channel
        LOG.debug("Ending trivia session; #%s in %s", channel, channel.guild)
        if session in self.trivia_sessions:
            self.trivia_sessions.remove(session)

    def get_trivia_list(self, category: str) -> List[tuple]:
        """Get the trivia list corresponding to the given category.

        :param str category:
            The desired category. Case sensitive.
        :return:
            A list of named tuples, with fields for `question` and `answers`.
        """
        path = self._get_lists_path()
        if path is None:
            return
        filename = "{}.txt".format(category)
        path = self._get_lists_path() / filename
        return parse_trivia_list(str(path))

    def _get_trivia_session(self, channel: discord.TextChannel) -> TriviaSession:
        return next((session for session in self.trivia_sessions
                     if session.ctx.channel == channel), None)

    def _get_lists_path(self) -> pathlib.Path:
        # Once the bot data path is configurable,
        #  we will get the path from the bot.
        ret = pathlib.Path(self.lists_dir)
        if ret.exists():
            return ret

    def _category_exists(self, category: str) -> bool:
        filename = "{}.txt".format(category)
        path = pathlib.Path(self._get_lists_path() / filename)
        return path.is_file()
