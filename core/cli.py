import argparse
import asyncio
import logging.handlers
import logging
import os
import sys
from pathlib import Path
from typing import Tuple
from copy import deepcopy

from core.global_checks import init_global_checks
from core.events import init_events
from core.core_commands import Core
from core.dev_commands import Dev
from core.cog_manager import CogManagerUI
from core.data_manager import basic_config_default, load_basic_configuration, core_data_path
from core.json_io import JsonIO
from core.bot import Red
from core.sentry_setup import init_sentry_logging

import appdirs


def confirm(m=""):
    return input(m).lower().strip() in ("y", "yes")


def interactive_config(red, token_set, prefix_set):
    loop = asyncio.get_event_loop()
    token = ""

    print("Red - Discord Bot | Configuration process\n")

    if not token_set:
        print("Please enter a valid token:")
        while not token:
            token = input("> ")
            if not len(token) >= 50:
                print("That doesn't look like a valid token.")
                token = ""
            if token:
                loop.run_until_complete(red.db.token.set(token))

    if not prefix_set:
        prefix = ""
        print("\nPick a prefix. A prefix is what you type before a "
              "command. Example:\n"
              "!help\n^ The exclamation mark is the prefix in this case.\n"
              "Can be multiple characters. You will be able to change it "
              "later and add more of them.\nChoose your prefix:\n")
        while not prefix:
            prefix = input("Prefix> ")
            if len(prefix) > 10:
                print("Your prefix seems overly long. Are you sure it "
                      "is correct? (y/n)")
                if not confirm("> "):
                    prefix = ""
            if prefix:
                loop.run_until_complete(red.db.prefix.set([prefix]))

    ask_sentry(red)

    return token


def ask_sentry(red: Red):
    loop = asyncio.get_event_loop()
    print("\nThank you for installing Red V3 alpha! The current version\n"
          " is not suited for production use and is aimed at testing\n"
          " the current and upcoming featureset, that's why we will\n"
          " also collect the fatal error logs to help us fix any new\n"
          " found issues in a timely manner. If you wish to opt in\n"
          " the process please type \"yes\":\n")
    if not confirm("> "):
        loop.run_until_complete(red.db.enable_sentry.set(False))
    else:
        loop.run_until_complete(red.db.enable_sentry.set(True))
        print("\nThank you for helping us with the development process!")


def parse_cli_flags():
    parser = argparse.ArgumentParser(description="Red - Discord Bot")
    parser.add_argument("--owner", type=int,
                        help="ID of the owner. Only who hosts "
                             "Red should be owner, this has "
                             "serious security implications.")
    parser.add_argument("--co-owner", type=int, action="append", default=[],
                        help="ID of a co-owner. Only people who have access "
                             "to the system that is hosting Red should be  "
                             "co-owners, as this gives them complete access "
                             "to the system's data. This has serious "
                             "security implications if misused. Can be "
                             "multiple.")
    parser.add_argument("--prefix", "-p", action="append",
                        help="Global prefix. Can be multiple")
    parser.add_argument("--no-prompt",
                        action="store_true",
                        help="Disables console inputs. Features requiring "
                             "console interaction could be disabled as a "
                             "result")
    parser.add_argument("--no-cogs",
                        action="store_true",
                        help="Starts Red with no cogs loaded, only core")
    parser.add_argument("--self-bot",
                        action='store_true',
                        help="Specifies if Red should log in as selfbot")
    parser.add_argument("--not-bot",
                        action='store_true',
                        help="Specifies if the token used belongs to a bot "
                             "account.")
    parser.add_argument("--dry-run",
                        action="store_true",
                        help="Makes Red quit with code 0 just before the "
                             "login. This is useful for testing the boot "
                             "process.")
    parser.add_argument("--debug",
                        action="store_true",
                        help="Sets the loggers level as debug")
    parser.add_argument("--dev",
                        action="store_true",
                        help="Enables developer mode")
    parser.add_argument("config",
                        nargs='?',
                        help="Path to config generated on initial setup.")

    args = parser.parse_args()

    if args.prefix:
        args.prefix = sorted(args.prefix, reverse=True)
    else:
        args.prefix = []

    return args


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
        '%(asctime)s %(levelname)s %(module)s %(funcName)s %(lineno)d: '
        '%(message)s',
        datefmt="[%d/%m/%Y %H:%M]")

    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setFormatter(red_format)

    if cli_flags.debug:
        os.environ['PYTHONASYNCIODEBUG'] = '1'
        logger.setLevel(logging.DEBUG)
    else:
        logger.setLevel(logging.WARNING)

    logfile_path = core_data_path() / 'red.log'
    fhandler = logging.handlers.RotatingFileHandler(
        filename=str(logfile_path), encoding='utf-8', mode='a',
        maxBytes=10**7, backupCount=5)
    fhandler.setFormatter(red_format)

    logger.addHandler(fhandler)
    logger.addHandler(stdout_handler)

    # Sentry stuff
    sentry_logger = logging.getLogger("red.sentry")
    sentry_logger.setLevel(logging.WARNING)

    return logger, sentry_logger


def sentry_setup(red: Red, sentry_log: logging.Logger):
    if red.db.enable_sentry() is None:
        ask_sentry(red)

    if red.db.enable_sentry():
        init_sentry_logging(red, sentry_log)


def determine_main_folder() -> Path:
    return Path(os.path.dirname(__file__)).resolve().parent


def setup_cog_install_location(red: Red):
    pass


def setup(cli_flags, bot_dir: Path) -> Tuple[Red, str, logging.Logger, logging.Logger]:
    log, sentry_log = init_loggers(cli_flags)
    description = "Red v3 - Alpha"
    red = Red(cli_flags, description=description, pm_help=None,
              bot_dir=bot_dir)
    init_global_checks(red)
    init_events(red, cli_flags)

    red.add_cog(Core())
    red.add_cog(CogManagerUI())

    if cli_flags.dev:
        red.add_cog(Dev())

    token = os.environ.get("RED_TOKEN", red.db.token())
    prefix = cli_flags.prefix or red.db.prefix()

    if token is None or not prefix:
        if cli_flags.no_prompt is False:
            new_token = interactive_config(red, token_set=bool(token),
                                           prefix_set=bool(prefix))
            if new_token:
                token = new_token
        else:
            log.critical("Token and prefix must be set in order to login.")
            sys.exit(1)

    sentry_setup(red, sentry_log)

    setup_cog_install_location(red)
    return red, token, log, sentry_log


def basic_setup():
    """
    Creates the data storage folder.
    :return:
    """
    proj_name = "Red-DiscordBot"
    author = "Twentysix26 et al."

    default_data_dir = Path(appdirs.user_data_dir(proj_name, author))

    print("Hello! Before we begin the full configuration process we need to"
          " gather some initial information about where you'd like us"
          " to store your bot's data. We've attempted to figure out a"
          " sane default data location which is printed below. If you don't"
          " want to change this default please press [ENTER], otherwise"
          " input your desired data location.")
    print()
    print("Default: {}".format(default_data_dir))

    new_path = input('> ')

    if new_path != '':
        new_path = Path(new_path)
        default_data_dir = new_path

    if not default_data_dir.exists():
        try:
            default_data_dir.mkdir(parents=True, exist_ok=True)
        except OSError:
            print("We were unable to create your chosen directory."
                  " You may need to restart this process with admin"
                  " privileges.")
            sys.exit(1)

    print("You have chosen {} to be your data directory."
          "".format(default_data_dir))
    if not confirm("Please confirm (y/n):"):
        print("Please start the process over.")
        sys.exit(0)

    default_dirs = deepcopy(basic_config_default)
    default_dirs['DATA_PATH'] = str(default_data_dir.resolve())

    conf_path = Path.cwd() / 'config.json'
    saver = JsonIO(conf_path)

    saver._save_json(default_dirs)

    print("Your configuration file has been saved to this directory:"
          "\n\n{}\n\nFrom here on out you must run Red with the"
          " configuration file as a positional argument. You may"
          " move the configuration file wherever you wish.".format(
              conf_path
          ))

    load_basic_configuration(conf_path)
