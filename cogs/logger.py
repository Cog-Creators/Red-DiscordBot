import logging
from discord.ext import commands
from cogs.utils import checks
from cogs.utils.chat_formatting import box
from __main__ import send_cmd_help
from cogs.utils.dataIO import dataIO
import os

try:
    import tabulate
except:
    tabulate = None

log = logging.getLogger("red.logger")
log.setLevel(logging.DEBUG)


class Logger:
    """Messes with the bot loggers"""

    def __init__(self, bot):
        self.bot = bot
        self.levels = [
            "debug",
            "warning",
            "critical",
            "info",
            "error",
            "notset"
        ]
        self._saved_levels = dataIO.load_json('data/logger/saved_levels.json')

    def _get_levels(self, loggers):
        ret = []
        for logger in loggers:
            logger_lvl = logging.getLogger(logger).getEffectiveLevel()
            ret.append(self._int_to_name(logger_lvl))
        log.debug("Level list:\n\t{}".format(ret))
        return ret

    def _get_loggers(self):
        ret = []
        for logname in logging.Logger.manager.loggerDict:
            ret.append(logname)
        ret = sorted(ret)
        return ret

    def _get_red_loggers(self):
        loggers = self._get_loggers()
        ret = []
        for logger in loggers:
            if logger.lower().startswith("red") or \
                    logger.lower().startswith("cogs"):
                ret.append(logger)
        ret = sorted(ret)
        log.debug("Logger list:\n\t{}".format(ret))
        return ret

    def _int_to_name(self, level_int):
        if level_int == logging.CRITICAL:
            return "Critical"
        elif level_int == logging.ERROR:
            return "Error"
        elif level_int == logging.WARNING:
            return "Warning"
        elif level_int == logging.INFO:
            return "Info"
        elif level_int == logging.DEBUG:
            return "Debug"
        elif level_int == logging.NOTSET:
            return "Not set"
        return level_int

    def _name_to_level(self, level_str):
        try:
            level = int(level_str)
        except:
            pass
        else:
            return str(level)

        if level_str.lower() in self.levels:
            return getattr(logging, level_str.upper())

    async def _reset_saved_loggers(self):
        all_loggers = self._get_loggers()
        for logname, info in self._saved_levels.items():
            level = info.get("override")
            if logname in all_loggers:
                curr_log = logging.getLogger(logname)
                curr_log.setLevel(level)

    def _rollover(self, name):
        curr_log = logging.getLogger(name)

        for handler in curr_log.handlers:
            try:
                handler.doRollover()
            except AttributeError:
                pass

    def _save_levels(self):
        dataIO.save_json('data/logger/saved_levels.json', self._saved_levels)

    def _set_level(self, name, level):
        curr_log = logging.getLogger(name)
        default = curr_log.getEffectiveLevel()
        curr_log.setLevel(level)
        self._saved_levels[name] = {"override": level, "default": default}
        self._save_levels()

    @commands.group(pass_context=True)
    @checks.is_owner()
    async def logger(self, ctx):
        """Messes with the bot loggers"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @logger.command(pass_context=True, name="list")
    async def logger_list(self, ctx):
        """Lists logs and their levels."""
        loggers = self._get_red_loggers()
        levels = self._get_levels(loggers)
        ret = zip(loggers, levels)
        headers = ["Logger", "Level"]
        msg = tabulate.tabulate(ret, headers, tablefmt="psql")
        await self.bot.say(box(msg))

    @logger.command(name="reload")
    async def logger_reload(self):
        """Reloads saved levels, just in case"""
        await self._reset_saved_loggers()
        await self.bot.say("All levels reloaded.")

    @logger.command(pass_context=True, name="reset")
    async def logger_reset(self, ctx, name):
        """Resets a log to it's default level"""
        if name not in self._get_loggers():
            await self.bot.say("Invalid logger.")
            return
        elif name not in self._get_red_loggers():
            await self.bot.say("Not a Red logger.")
            return
        elif name not in self._saved_levels:
            await self.bot.say("Haven't overridden this logger.")
            return

        curr_log = logging.getLogger(name)
        curr_log.setLevel(self._saved_levels[name].get("default"))
        del self._saved_levels[name]
        self._save_levels()

        await self.bot.say("Level reset.")

    @logger.command(pass_context=True, name="rollover")
    async def logger_rollover(self, ctx, name):
        """Rolls over a log"""
        if name not in self._get_loggers():
            await self.bot.say("Invalid logger.")
            return
        elif name not in self._get_red_loggers():
            await self.bot.say("Not a Red logger.")
            return

        self._rollover(name)
        await self.bot.say("Rolled {}.".format(name))

    @logger.command(pass_context=True, name="setlevel")
    async def logger_setlevel(self, ctx, name, level):
        """Sets level for a logger"""
        if name not in self._get_loggers():
            await self.bot.say("Invalid logger.")
            return
        elif name not in self._get_red_loggers():
            await self.bot.say("Not a Red logger.")
            return

        try:
            level = self._name_to_level(level)
        except:
            await self.bot.say("Bad level.")
        else:
            self._set_level(name, level)
            await self.bot.say("{} set to logging.{}".format(
                name, self._int_to_name(level).upper()))


def check_files():
    if not os.path.exists('data/logger/saved_levels.json'):
        try:
            os.mkdir('data/logger')
        except FileExistsError:
            pass
        dataIO.save_json('data/logger/saved_levels.json', {})


def setup(bot):
    if tabulate is None:
        raise RuntimeError("Must run `pip install tabulate` to use Logger.")
    check_files()
    n = Logger(bot)
    bot.add_cog(n)
    bot.add_listener(n._reset_saved_loggers, 'on_ready')
