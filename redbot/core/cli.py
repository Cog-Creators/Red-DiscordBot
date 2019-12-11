import argparse
import asyncio
import logging
import sys
from typing import Optional


def confirm(text: str, default: Optional[bool] = None) -> bool:
    if default is None:
        options = "y/n"
    elif default is True:
        options = "Y/n"
    elif default is False:
        options = "y/N"
    else:
        raise TypeError(f"expected bool, not {type(default)}")

    while True:
        try:
            value = input(f"{text}: [{options}] ").lower().strip()
        except (KeyboardInterrupt, EOFError):
            print("\nAborted!")
            sys.exit(1)
        if value in ("y", "yes"):
            return True
        if value in ("n", "no"):
            return False
        if value == "":
            if default is not None:
                return default
        print("Error: invalid input")


def interactive_config(red, token_set, prefix_set, *, print_header=True):
    loop = asyncio.get_event_loop()
    token = ""

    if print_header:
        print("Red - Discord Bot | Configuration process\n")

    if not token_set:
        print("Please enter a valid token:")
        while not token:
            token = input("> ")
            if not len(token) >= 50:
                print("That doesn't look like a valid token.")
                token = ""
            if token:
                loop.run_until_complete(red._config.token.set(token))

    if not prefix_set:
        prefix = ""
        print(
            "\nPick a prefix. A prefix is what you type before a "
            "command. Example:\n"
            "!help\n^ The exclamation mark is the prefix in this case.\n"
            "The prefix can be multiple characters. You will be able to change it "
            "later and add more of them.\nChoose your prefix:\n"
        )
        while not prefix:
            prefix = input("Prefix> ")
            if len(prefix) > 10:
                if not confirm("Your prefix seems overly long. Are you sure that it's correct?"):
                    prefix = ""
            if prefix:
                loop.run_until_complete(red._config.prefix.set([prefix]))

    return token


def parse_cli_flags(args):
    parser = argparse.ArgumentParser(
        description="Red - Discord Bot", usage="redbot <instance_name> [arguments]"
    )
    parser.add_argument("--version", "-V", action="store_true", help="Show Red's current version")
    parser.add_argument(
        "--list-instances",
        action="store_true",
        help="List all instance names setup with 'redbot-setup'",
    )
    parser.add_argument(
        "--edit",
        action="store_true",
        help="Edit the instance. This can be done without console interaction "
        "by passing --no-prompt and arguments that you want to change (available arguments: "
        "--edit-instance-name, --edit-data-path, --copy-data, --owner, --token).",
    )
    parser.add_argument(
        "--edit-instance-name",
        type=str,
        help="New name for the instance. This argument only works with --edit argument passed.",
    )
    parser.add_argument(
        "--overwrite-existing-instance",
        action="store_true",
        help="Confirm overwriting of existing instance when changing name."
        " This argument only works with --edit argument passed.",
    )
    parser.add_argument(
        "--edit-data-path",
        type=str,
        help=(
            "New data path for the instance. This argument only works with --edit argument passed."
        ),
    )
    parser.add_argument(
        "--copy-data",
        action="store_true",
        help="Copy data from old location. This argument only works "
        "with --edit and --edit-data-path arguments passed.",
    )
    parser.add_argument(
        "--owner",
        type=int,
        help="ID of the owner. Only who hosts "
        "Red should be owner, this has "
        "serious security implications if misused.",
    )
    parser.add_argument(
        "--co-owner",
        type=int,
        default=[],
        nargs="+",
        help="ID of a co-owner. Only people who have access "
        "to the system that is hosting Red should be  "
        "co-owners, as this gives them complete access "
        "to the system's data. This has serious "
        "security implications if misused. Can be "
        "multiple.",
    )
    parser.add_argument("--prefix", "-p", action="append", help="Global prefix. Can be multiple")
    parser.add_argument(
        "--no-prompt",
        action="store_true",
        help="Disables console inputs. Features requiring "
        "console interaction could be disabled as a "
        "result",
    )
    parser.add_argument(
        "--no-cogs", action="store_true", help="Starts Red with no cogs loaded, only core"
    )
    parser.add_argument(
        "--load-cogs",
        type=str,
        nargs="+",
        help="Force loading specified cogs from the installed packages. "
        "Can be used with the --no-cogs flag to load these cogs exclusively.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Makes Red quit with code 0 just before the "
        "login. This is useful for testing the boot "
        "process.",
    )
    parser.add_argument(
        "--debug",
        action="store_const",
        dest="logging_level",
        const=logging.DEBUG,
        default=logging.INFO,
        help="Sets the loggers level as debug",
    )
    parser.add_argument("--dev", action="store_true", help="Enables developer mode")
    parser.add_argument(
        "--mentionable",
        action="store_true",
        help="Allows mentioning the bot as an alternative to using the bot prefix",
    )
    parser.add_argument(
        "--rpc",
        action="store_true",
        help="Enables the built-in RPC server. Please read the docs prior to enabling this!",
    )
    parser.add_argument(
        "--rpc-port",
        type=int,
        default=6133,
        help="The port of the built-in RPC server to use. Default to 6133.",
    )
    parser.add_argument("--token", type=str, help="Run Red with the given token.")
    parser.add_argument(
        "--no-instance",
        action="store_true",
        help=(
            "Run Red without any existing instance. "
            "The data will be saved under a temporary folder "
            "and deleted on next system restart."
        ),
    )
    parser.add_argument(
        "instance_name", nargs="?", help="Name of the bot instance created during `redbot-setup`."
    )

    args = parser.parse_args(args)

    if args.prefix:
        args.prefix = sorted(args.prefix, reverse=True)
    else:
        args.prefix = []

    return args
