#!/usr/bin/env python

# Discord Version check

import asyncio
import json
import logging
import os
import sys

import discord

# Set the event loop policies here so any subsequent `get_event_loop()`
# calls, in particular those as a result of the following imports,
# return the correct loop object.
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
elif sys.implementation.name == "cpython":
    # Let's not force this dependency, uvloop is much faster on cpython
    try:
        import uvloop
    except ImportError:
        uvloop = None
        pass
    else:
        asyncio.set_event_loop_policy(uvloop.EventLoopPolicy())

import redbot.logging
from redbot.core.bot import Red, ExitCodes
from redbot.core.cog_manager import CogManagerUI
from redbot.core.global_checks import init_global_checks
from redbot.core.events import init_events
from redbot.core.cli import interactive_config, confirm, parse_cli_flags
from redbot.core.core_commands import Core, license_info_command
from redbot.core.dev_commands import Dev
from redbot.core import __version__, modlog, bank, data_manager, drivers
from signal import SIGTERM


log = logging.getLogger("red.main")

#
#               Red - Discord Bot v3
#
#         Made by Twentysix, improved by many
#


async def _get_prefix_and_token(red, indict):
    """
    Again, please blame <@269933075037814786> for this.
    :param indict:
    :return:
    """
    indict["token"] = await red._config.token()
    indict["prefix"] = await red._config.prefix()


def list_instances():
    if not data_manager.config_file.exists():
        print(
            "No instances have been configured! Configure one "
            "using `redbot-setup` before trying to run the bot!"
        )
        sys.exit(1)
    else:
        with data_manager.config_file.open(encoding="utf-8") as fs:
            data = json.load(fs)
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
        print("Current Version: {}".format(__version__))
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
        data_manager.create_temp_config()
    loop = asyncio.get_event_loop()

    data_manager.load_basic_configuration(cli_flags.instance_name)
    driver_cls = drivers.get_driver_class()
    loop.run_until_complete(driver_cls.initialize(**data_manager.storage_details()))
    redbot.logging.init_logging(
        level=cli_flags.logging_level, location=data_manager.core_data_path() / "logs"
    )

    log.debug("====Basic Config====")
    log.debug("Data Path: %s", data_manager._base_data_path())
    log.debug("Storage Type: %s", data_manager.storage_type())

    red = Red(
        cli_flags=cli_flags, description=description, dm_help=None, fetch_offline_members=True
    )
    loop.run_until_complete(red._maybe_update_config())
    init_global_checks(red)
    init_events(red, cli_flags)

    # lib folder has to be in sys.path before trying to load any 3rd-party cog (GH-3061)
    # We might want to change handling of requirements in Downloader at later date
    LIB_PATH = data_manager.cog_data_path(raw_name="Downloader") / "lib"
    LIB_PATH.mkdir(parents=True, exist_ok=True)
    if str(LIB_PATH) not in sys.path:
        sys.path.append(str(LIB_PATH))

    red.add_cog(Core(red))
    red.add_cog(CogManagerUI())
    red.add_command(license_info_command)
    if cli_flags.dev:
        red.add_cog(Dev())
    # noinspection PyProtectedMember
    loop.run_until_complete(modlog._init(red))
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
        db_token = loop.run_until_complete(red._config.token())
        if db_token and not cli_flags.no_prompt:
            print("\nDo you want to reset the token? (y/n)")
            if confirm("> "):
                loop.run_until_complete(red._config.token.set(""))
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
