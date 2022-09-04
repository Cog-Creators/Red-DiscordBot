"""
The original implementation of this cog was heavily based on
RoboDanny's REPL cog which can be found here:
https://github.com/Rapptz/RoboDanny/blob/f13e1c9a6a7205e50de6f91fa5326fc7113332d3/cogs/repl.py

Copyright (c) 2017-present Cog Creators
Copyright (c) 2016-2017 Rapptz

The original copy was distributed under MIT License and this derivative work
is distributed under GNU GPL Version 3.
"""

import ast
import asyncio
import aiohttp
import inspect
import io
import textwrap
import traceback
import types
import re
import sys
from contextlib import redirect_stdout
from copy import copy

import discord

from . import checks, commands
from .commands import NoParseOptional as Optional
from .i18n import Translator, cog_i18n
from .utils import chat_formatting
from .utils.chat_formatting import pagify
from .utils.predicates import MessagePredicate

_ = Translator("Dev", __file__)

START_CODE_BLOCK_RE = re.compile(r"^((```py(thon)?)(?=\s)|(```))")


@cog_i18n(_)
class Dev(commands.Cog):
    """Various development focused utilities."""

    async def red_delete_data_for_user(self, **kwargs):
        """
        Because despite my best efforts to advise otherwise,
        people use ``--dev`` in production
        """
        return

    def __init__(self):
        super().__init__()
        self._last_result = None
        self.sessions = {}
        self.env_extensions = {}

    @staticmethod
    def async_compile(source, filename, mode):
        return compile(source, filename, mode, flags=ast.PyCF_ALLOW_TOP_LEVEL_AWAIT, optimize=0)

    @staticmethod
    async def maybe_await(coro):
        for i in range(2):
            if inspect.isawaitable(coro):
                coro = await coro
            else:
                return coro
        return coro

    @staticmethod
    def cleanup_code(content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith("```") and content.endswith("```"):
            return START_CODE_BLOCK_RE.sub("", content)[:-3]

        # remove `foo`
        return content.strip("` \n")

    @staticmethod
    def format_exception(
        exc: Exception, *, source: str, filename: str, line_offset: int = 0, skip_frames: int = 1
    ) -> str:
        """
        Format an exception to send to the user.

        This function makes a few alterations to the traceback:
        - First `skip_frames` frames are skipped so that we don't show the frames
          that are part of Red's code to the user
        - `FrameSummary` objects that we get from traceback module are updated
          with the string for the corresponding line of code as otherwise
          the generated traceback string wouldn't show user's code.
        - If `line_offset` is passed, this function subtracts it from line numbers
          in `FrameSummary` objects so that those numbers properly correspond to
          the code that was provided by the user. This is needed for cases where
          we wrap user's code in an async function before exec-ing it.
        """
        exc_type = type(exc)
        tb = exc.__traceback__
        for x in range(skip_frames):
            tb = tb.tb_next
        traceback_exc = traceback.TracebackException(exc_type, exc, tb)

        source_lines = source.splitlines(True)
        py311_or_above = sys.version_info >= (3, 11)
        stack_summary = traceback_exc.stack
        for idx, frame_summary in enumerate(stack_summary):
            if frame_summary.filename != filename:
                continue

            # line numbers are 1-based, the list indexes are 0-based
            line = source_lines[frame_summary.lineno - 1]
            # support for enhanced error locations in tracebacks
            if py311_or_above:
                frame_summary = traceback.FrameSummary(
                    frame_summary.filename,
                    frame_summary.lineno - line_offset,
                    frame_summary.name,
                    line=line,
                    end_lineno=frame_summary.end_lineno - line_offset,
                    colno=frame_summary.colno,
                    end_colno=frame_summary.end_colno,
                )
            else:
                frame_summary = traceback.FrameSummary(
                    frame_summary.filename,
                    frame_summary.lineno - line_offset,
                    frame_summary.name,
                    line=line,
                )
            stack_summary[idx] = frame_summary

        return "".join(traceback_exc.format())

    @staticmethod
    def get_pages(msg: str):
        """Pagify the given message for output to the user."""
        return pagify(msg, delims=["\n", " "], priority=True, shorten_by=10)

    @staticmethod
    def sanitize_output(ctx: commands.Context, input_: str) -> str:
        """Hides the bot's token from a string."""
        token = ctx.bot.http.token
        return re.sub(re.escape(token), "[EXPUNGED]", input_, re.I)

    def get_environment(self, ctx: commands.Context) -> dict:
        env = {
            "bot": ctx.bot,
            "ctx": ctx,
            "channel": ctx.channel,
            "author": ctx.author,
            "guild": ctx.guild,
            "message": ctx.message,
            "asyncio": asyncio,
            "aiohttp": aiohttp,
            "discord": discord,
            "commands": commands,
            "cf": chat_formatting,
            "_": self._last_result,
            "__name__": "__main__",
        }
        for name, value in self.env_extensions.items():
            try:
                env[name] = value(ctx)
            except Exception as exc:
                traceback.clear_frames(exc.__traceback__)
                env[name] = exc
        return env

    @commands.command()
    @checks.is_owner()
    async def debug(self, ctx, *, code):
        """Evaluate a statement of python code.

        The bot will always respond with the return value of the code.
        If the return value of the code is a coroutine, it will be awaited,
        and the result of that will be the bot's response.

        Note: Only one statement may be evaluated. Using certain restricted
        keywords, e.g. yield, will result in a syntax error. For multiple
        lines or asynchronous code, see [p]repl or [p]eval.

        Environment Variables:
            `ctx`      - the command invocation context
            `bot`      - the bot object
            `channel`  - the current channel object
            `author`   - the command author's member object
            `guild`    - the current guild object
            `message`  - the command's message object
            `_`        - the result of the last dev command
            `aiohttp`  - the aiohttp library
            `asyncio`  - the asyncio library
            `discord`  - the discord.py library
            `commands` - the redbot.core.commands module
            `cf`       - the redbot.core.utils.chat_formatting module
        """
        env = self.get_environment(ctx)
        code = self.cleanup_code(code)
        filename = "<debug command>"

        try:
            compiled = self.async_compile(code, filename, "eval")
        except SyntaxError as exc:
            await ctx.send_interactive(
                self.get_pages(
                    self.format_exception(exc, source=code, filename=filename, skip_frames=2)
                ),
                box_lang="py",
            )
            return

        try:
            result = await self.maybe_await(eval(compiled, env))
        except Exception as exc:
            await ctx.send_interactive(
                self.get_pages(self.format_exception(exc, source=code, filename=filename)),
                box_lang="py",
            )
            return

        self._last_result = result
        result = self.sanitize_output(ctx, result)

        await ctx.tick()
        await ctx.send_interactive(self.get_pages(result), box_lang="py")

    @commands.command(name="eval")
    @checks.is_owner()
    async def _eval(self, ctx, *, body: str):
        """Execute asynchronous code.

        This command wraps code into the body of an async function and then
        calls and awaits it. The bot will respond with anything printed to
        stdout, as well as the return value of the function.

        The code can be within a codeblock, inline code or neither, as long
        as they are not mixed and they are formatted correctly.

        Environment Variables:
            `ctx`      - the command invocation context
            `bot`      - the bot object
            `channel`  - the current channel object
            `author`   - the command author's member object
            `guild`    - the current guild object
            `message`  - the command's message object
            `_`        - the result of the last dev command
            `aiohttp`  - the aiohttp library
            `asyncio`  - the asyncio library
            `discord`  - the discord.py library
            `commands` - the redbot.core.commands module
            `cf`       - the redbot.core.utils.chat_formatting module
        """
        env = self.get_environment(ctx)
        body = self.cleanup_code(body)
        filename = "<eval command>"
        stdout = io.StringIO()

        to_compile = "async def func():\n%s" % textwrap.indent(body, "  ")

        try:
            compiled = self.async_compile(to_compile, filename, "exec")
            exec(compiled, env)
        except SyntaxError as exc:
            return await ctx.send_interactive(
                self.get_pages(
                    self.format_exception(
                        exc, source=to_compile, filename=filename, line_offset=1, skip_frames=2
                    )
                ),
                box_lang="py",
            )

        func = env["func"]
        result = None
        try:
            with redirect_stdout(stdout):
                result = await func()
        except Exception as exc:
            printed = stdout.getvalue() + self.format_exception(
                exc, source=to_compile, filename=filename, line_offset=1
            )
        else:
            printed = stdout.getvalue()
            await ctx.tick()

        if result is not None:
            self._last_result = result
            msg = f"{printed}{result}"
        else:
            msg = printed
        msg = self.sanitize_output(ctx, msg)

        await ctx.send_interactive(self.get_pages(msg), box_lang="py")

    @commands.group(invoke_without_command=True)
    @checks.is_owner()
    async def repl(self, ctx):
        """Open an interactive REPL.

        The REPL will only recognise code as messages which start with a
        backtick. This includes codeblocks, and as such multiple lines can be
        evaluated.

        Use `exit()` or `quit` to exit the REPL session, prefixed with
        a backtick so they may be interpreted.

        Environment Variables:
            `ctx`      - the command invocation context
            `bot`      - the bot object
            `channel`  - the current channel object
            `author`   - the command author's member object
            `guild`    - the current guild object
            `message`  - the command's message object
            `_`        - the result of the last dev command
            `aiohttp`  - the aiohttp library
            `asyncio`  - the asyncio library
            `discord`  - the discord.py library
            `commands` - the redbot.core.commands module
            `cf`       - the redbot.core.utils.chat_formatting module
        """
        if ctx.channel.id in self.sessions:
            if self.sessions[ctx.channel.id]:
                await ctx.send(
                    _("Already running a REPL session in this channel. Exit it with `quit`.")
                )
            else:
                await ctx.send(
                    _(
                        "Already running a REPL session in this channel. Resume the REPL with `{}repl resume`."
                    ).format(ctx.prefix)
                )
            return

        filename = "<repl session>"
        env = self.get_environment(ctx)
        env["__builtins__"] = __builtins__
        env["_"] = None
        self.sessions[ctx.channel.id] = True
        await ctx.send(
            _(
                "Enter code to execute or evaluate. `exit()` or `quit` to exit. `{}repl pause` to pause."
            ).format(ctx.prefix)
        )

        while True:
            response = await ctx.bot.wait_for("message", check=MessagePredicate.regex(r"^`", ctx))

            if not self.sessions[ctx.channel.id]:
                continue

            cleaned = self.cleanup_code(response.content)

            if cleaned in ("quit", "exit", "exit()"):
                await ctx.send(_("Exiting."))
                del self.sessions[ctx.channel.id]
                return

            executor = None
            if cleaned.count("\n") == 0:
                # single statement, potentially 'eval'
                try:
                    code = self.async_compile(cleaned, filename, "eval")
                except SyntaxError:
                    pass
                else:
                    executor = eval

            if executor is None:
                try:
                    code = self.async_compile(cleaned, filename, "exec")
                except SyntaxError as exc:
                    await ctx.send_interactive(
                        self.get_pages(
                            self.format_exception(
                                exc, source=cleaned, filename=filename, skip_frames=2
                            )
                        ),
                        box_lang="py",
                    )
                    continue

            env["message"] = response
            stdout = io.StringIO()

            msg = ""

            try:
                with redirect_stdout(stdout):
                    if executor is None:
                        result = types.FunctionType(code, env)()
                    else:
                        result = executor(code, env)
                    result = await self.maybe_await(result)
            except Exception as exc:
                value = stdout.getvalue()
                msg = value + self.format_exception(exc, source=cleaned, filename=filename)
            else:
                value = stdout.getvalue()
                if result is not None:
                    try:
                        msg = f"{value}{result}"
                    except Exception as exc:
                        msg = value + self.format_exception(exc, source=cleaned, filename=filename)
                    env["_"] = result
                elif value:
                    msg = f"{value}"

            msg = self.sanitize_output(ctx, msg)

            try:
                await ctx.send_interactive(self.get_pages(msg), box_lang="py")
            except discord.Forbidden:
                pass
            except discord.HTTPException as exc:
                await ctx.send(_("Unexpected error: `{}`").format(exc))

    @repl.command(aliases=["resume"])
    async def pause(self, ctx, toggle: Optional[bool] = None):
        """Pauses/resumes the REPL running in the current channel."""
        if ctx.channel.id not in self.sessions:
            await ctx.send(_("There is no currently running REPL session in this channel."))
            return

        if toggle is None:
            toggle = not self.sessions[ctx.channel.id]
        self.sessions[ctx.channel.id] = toggle

        if toggle:
            await ctx.send(_("The REPL session in this channel has been resumed."))
        else:
            await ctx.send(_("The REPL session in this channel is now paused."))

    @commands.guild_only()
    @commands.command()
    @checks.is_owner()
    async def mock(self, ctx, user: discord.Member, *, command):
        """Mock another user invoking a command.

        The prefix must not be entered.
        """
        msg = copy(ctx.message)
        msg.author = user
        msg.content = ctx.prefix + command

        ctx.bot.dispatch("message", msg)

    @commands.guild_only()
    @commands.command(name="mockmsg")
    @checks.is_owner()
    async def mock_msg(self, ctx, user: discord.Member, *, content: str = ""):
        """Dispatch a message event as if it were sent by a different user.

        Current message is used as a base (including attachments, embeds, etc.),
        the content and author of the message are replaced with the given arguments.

        Note: If `content` isn't passed, the message needs to contain embeds, attachments,
        or anything else that makes the message non-empty.
        """
        msg = ctx.message
        if not content and not msg.embeds and not msg.attachments and not msg.stickers:
            await ctx.send_help()
            return
        msg = copy(msg)
        msg.author = user
        msg.content = content

        ctx.bot.dispatch("message", msg)

    @commands.command()
    @checks.is_owner()
    async def bypasscooldowns(self, ctx, toggle: Optional[bool] = None):
        """Give bot owners the ability to bypass cooldowns.

        Does not persist through restarts."""
        if toggle is None:
            toggle = not ctx.bot._bypass_cooldowns
        ctx.bot._bypass_cooldowns = toggle

        if toggle:
            await ctx.send(_("Bot owners will now bypass all commands with cooldowns."))
        else:
            await ctx.send(_("Bot owners will no longer bypass all commands with cooldowns."))
