import asyncio
import functools
import logging
import uuid
from datetime import datetime, timedelta
from typing import NoReturn

import pytz
import discord
from redbot.core import commands, checks
from redbot.core.config import Config
from redbot.core.i18n import Translator, cog_i18n
from redbot.core.utils.chat_formatting import pagify, humanize_timedelta

log = logging.getLogger("red.cogs.scheduler")
_ = Translator("Dormmamu, I've come to bargain.", __file__)

@cog_i18n(_)
class Scheduler(commands.Cog):
    """
    A cog for scheduling commands.

    Docs for advanced usage available at <TODO: Docs link>
    """

    def __init__(self, bot):
        self.bot = bot
        self.config = Config.get_conf(self, identifier=78631113035100160)
        self.config.init_custom("SCHEDULED_COMMANDS", 2)
        self.config.register_custom(
            "SCHEDULED_COMMANDS",
            command="", # exact string minus prefix which is to be invoked
            start=0,  # naive unix timestamp, to be localized.
            user_id=0,
            channel_id=0,
            recur=None, # optional, seconds between recurring commands.
            snooze_until=None, # optional, same type as start.
            guild_id=None, # optional, just here for convieneince of fetching during management commands.
            tz_info="UTC", # tz code created with. This can be updated by the author.
        )
        self.main_loop_task = bot.loop.create_task(self.main_loop())
        self.main_loop_task.add_done_callback(self.crashed_loop_handler)
        self.extra_tasks = {}
        self._crash_count = 0
    
    def cog_unload(self):
        self.main_loop_task.cancel()
        for task in self.extra_tasks.values():
            task.cancel()
    
    def crashed_loop_handler(self, fut):
        try:
            fut.exception()
        except asyncio.CancelledError:
            log.debug("Scheduler loop cancelled, assuming cog unload.")
        except Exception:
            if self._crash_count < 3 and log.getEffectiveLevel() == logging.DEBUG:
                log.exception("Scheduler loop crashed less than 3 times, restarting (debug enabled, otherwise would crash)")
                self.main_loop_task = self.bot.loop.create_task(self.main_loop())
                self.main_loop_task.add_done_callback(self.crashed_loop_handler)
                self._crash_count += 1
            else:
                log.exception("Scheduler loop crashed, assuming major issue, not restarting.")
        else:
            log.debug("Hey, an infinite loop died without being cancelled, this isn't supposed to ever happen.")

    async def main_loop(self) -> NoReturn:
        await self.bot.wait_until_ready()
        while True:
            run_next = await self.load_tasks()
            await asyncio.sleep(run_next)
    
    async def load_tasks(self) -> float:
        pass

    async def task_wrapper(self, task):
        await asyncio.sleep(task.get_timedelta())
        message = task.get_fake_message()
        context = await self.bot.get_context(message)
        context.assume_yes = True
        await self.bot.invoke(context)
        # let's not abuse on_message and break logging cogs
        self.bot.dispatch("red_scheduled_command_message", message)
    
    def done_command_task_callback(self, task, fut):
        try:
            fut.exception()
        except asyncio.CancelledError:
            pass
        except Exception:
            log.exception(f"Task died, taskinfo: {task.debuginfo}")
        else:
            self.extra_tasks.pop(task.uuid, None)