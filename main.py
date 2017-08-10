from pathlib import Path

from core.bot import ExitCodes
from core.data_manager import load_basic_configuration
from core.cli import confirm, parse_cli_flags, setup, basic_setup, determine_main_folder
import asyncio
import discord
import sys

#
#               Red - Discord Bot v3
#
#         Made by Twentysix, improved by many
#

if discord.version_info.major < 1:
    print("You are not running the rewritten version of discord.py.\n\n"
          "In order to use Red v3 you MUST be running d.py version"
          " >= 1.0.0.")
    sys.exit(1)


if __name__ == '__main__':
    cli_flags = parse_cli_flags()

    if cli_flags.config:
        load_basic_configuration(Path(cli_flags.config).resolve())
    else:
        basic_setup()

    red, token, log, sentry_log = setup(cli_flags, determine_main_folder())

    loop = asyncio.get_event_loop()
    cleanup_tasks = True

    try:
        loop.run_until_complete(red.start(token, bot=not cli_flags.not_bot))
    except discord.LoginFailure:
        cleanup_tasks = False  # No login happened, no need for this
        log.critical("This token doesn't seem to be valid. If it belongs to "
                     "a user account, remember that the --not-bot flag "
                     "must be used. For self-bot functionalities instead, "
                     "--self-bot")
        db_token = red.db.token()
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
        sentry_log.critical("Fatal Exception", exc_info=e)
        loop.run_until_complete(red.logout())
    finally:
        if cleanup_tasks:
            pending = asyncio.Task.all_tasks(loop=red.loop)
            gathered = asyncio.gather(*pending, loop=red.loop)
            gathered.cancel()
            red.loop.run_until_complete(gathered)
            gathered.exception()

        sys.exit(red._shutdown_mode.value)
