import argparse
import asyncio

from redbot.core.bot import Red


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
                print("Your prefix seems overly long. Are you sure that it's correct? (y/n)")
                if not confirm("> "):
                    prefix = ""
            if prefix:
                loop.run_until_complete(red.db.prefix.set([prefix]))

    ask_sentry(red)

    return token


def ask_sentry(red: Red):
    loop = asyncio.get_event_loop()
    print(
        "\nThank you for installing Red V3! Red is constantly undergoing\n"
        " improvements, and we would like to ask if you are comfortable with\n"
        " the bot automatically submitting fatal error logs to the development\n"
        ' team. If you wish to opt into the process please type "yes":\n'
    )
    if not confirm("> "):
        loop.run_until_complete(red.db.enable_sentry.set(False))
    else:
        loop.run_until_complete(red.db.enable_sentry.set(True))
        print("\nThank you for helping us with the development process!")


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
        nargs="*",
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
        nargs="*",
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
    parser.add_argument("--debug", action="store_true", help="Sets the loggers level as debug")
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
