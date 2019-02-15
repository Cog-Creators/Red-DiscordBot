#!/usr/bin/env python

# Discord Version check

import sys
import discord
from redbot.core.bot import Red, ExitCodes
from redbot.core.cog_manager import CogManagerUI
from redbot.core.data_manager import create_temp_config, load_basic_configuration, config_file
from redbot.core.json_io import JsonIO
from redbot.core.global_checks import init_global_checks
from redbot.core.events import init_events
from redbot.core.cli import interactive_config, confirm, parse_cli_flags
from redbot.core.core_commands import Core
from redbot.core.dev_commands import Dev
from redbot.core import modlog, bank
from signal import SIGTERM
import asyncio
import logging.handlers
import logging
import os

# Let's not force this dependency, uvloop is much faster on cpython
if sys.implementation.name == "cpython":
    try:
        import uvloop
    except ImportError:
        pass
    else:
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

if sys.platform == "win32":
    asyncio.set_event_loop(asyncio.ProactorEventLoop())


#
#               Red - Discord Bot v3
#
#         Made by Twentysix, improved by many
#


def init_loggers(cli_flags):
    # d.py stuff
    dpy_logger = logging.getLogger("discord")
    dpy_logger.setLevel(logging.WARNING)
    console = logging.StreamHandler()
    console.setLevel(logging.WARNING)
    dpy_logger.addHandler(console)

    # Red stuff

    logger = logging.getLogger("red")

    red_format = logging.Formatter(
        "%(asctime)s %(levelname)s %(module)s %(funcName)s %(lineno)d: %(message)s",
        datefmt="[%d/%m/%Y %H:%M]",
    )

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(red_format)

    if cli_flags.debug:
        os.environ["PYTHONASYNCIODEBUG"] = "1"
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.INFO)

    from redbot.core.data_manager import core_data_path

    logfile_path = core_data_path() / "red.log"
    fhandler = logging.handlers.RotatingFileHandler(
        filename=str(logfile_path), encoding="utf-8", mode="a", maxBytes=10 ** 7, backupCount=5
    )
    fhandler.setFormatter(red_format)

    logger.addHandler(fhandler)
    logger.addHandler(stdout_handler)

    return logger


async def _get_prefix_and_token(red, indict):
    """
    Again, please blame <@269933075037814786> for this.
    :param indict:
    :return:
    """
    indict["token"] = await red.db.token()
    indict["prefix"] = await red.db.prefix()


def list_instances():
    if not config_file.exists():
        print(
            "No instances have been configured! Configure one "
            "using `redbot-setup` before trying to run the bot!"
        )
        sys.exit(1)
    else:
        data = JsonIO(config_file)._load_json()
        text = "Configured Instances:\n\n"
        for instance_name in sorted(data.keys()):
            text += "{}\n".format(instance_name)
        print(text)
        sys.exit(0)


async def sigterm_handler(red, log):
    log.info("SIGTERM received. Quitting...")
    await red.shutdown(restart=False)


def main():
    description = "Red V3"
    cli_flags = parse_cli_flags(sys.argv[1:])
    if cli_flags.list_instances:
        list_instances()
    elif cli_flags.version:
        print(description)
        sys.exit(0)
    elif not cli_flags.instance_name and not cli_flags.no_instance:
        print("Error: No instance name was provided!")
        sys.exit(1)
    if cli_flags.no_instance:
        print(
            "\033[1m"
            "Warning: The data will be placed in a temporary folder and removed on next system "
            "reboot."
            "\033[0m"
        )
        cli_flags.instance_name = "temporary_red"
        create_temp_config()
    load_basic_configuration(cli_flags.instance_name)
    log = init_loggers(cli_flags)
    loop = asyncio.get_event_loop()
    red = Red(cli_flags=cli_flags, description=description, pm_help=None)
    init_global_checks(red)
    init_events(red, cli_flags)
    loop.run_until_complete(red.cog_mgr.initialize())
    red.add_cog(Core(red))
    red.add_cog(CogManagerUI())
    if cli_flags.dev:
        red.add_cog(Dev())
    # noinspection PyProtectedMember
    modlog._init()
    # noinspection PyProtectedMember
    bank._init()
    if os.name == "posix":
        loop.add_signal_handler(SIGTERM, lambda: asyncio.ensure_future(sigterm_handler(red, log)))
    tmp_data = {}
    loop.run_until_complete(_get_prefix_and_token(red, tmp_data))
    token = os.environ.get("RED_TOKEN", tmp_data["token"])
    if cli_flags.token:
        token = cli_flags.token
    prefix = cli_flags.prefix or tmp_data["prefix"]
    if not (token and prefix):
        if cli_flags.no_prompt is False:
            new_token = interactive_config(red, token_set=bool(token), prefix_set=bool(prefix))
            if new_token:
                token = new_token
        else:
            log.critical("Token and prefix must be set in order to login.")
            sys.exit(1)
    loop.run_until_complete(_get_prefix_and_token(red, tmp_data))

    if cli_flags.dry_run:
        loop.run_until_complete(red.http.close())
        sys.exit(0)
    try:
        loop.run_until_complete(red.start(token, bot=True))
    except discord.LoginFailure:
        log.critical("This token doesn't seem to be valid.")
        db_token = loop.run_until_complete(red.db.token())
        if db_token and not cli_flags.no_prompt:
            print("\nDo you want to reset the token? (y/n)")
            if confirm("> "):
                loop.run_until_complete(red.db.token.set(""))
                print("Token has been reset.")
    except KeyboardInterrupt:
        log.info("Keyboard interrupt detected. Quitting...")
        loop.run_until_complete(red.logout())
        red._shutdown_mode = ExitCodes.SHUTDOWN
    except Exception as e:
        log.critical("Fatal exception", exc_info=e)
        loop.run_until_complete(red.logout())
    finally:
        pending = asyncio.Task.all_tasks(loop=red.loop)
        gathered = asyncio.gather(*pending, loop=red.loop, return_exceptions=True)
        gathered.cancel()
        try:
            loop.run_until_complete(red.rpc.close())
        except AttributeError:
            pass

        sys.exit(red._shutdown_mode.value)


if __name__ == "__main__":
    main()
