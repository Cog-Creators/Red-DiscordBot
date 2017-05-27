import argparse
import asyncio


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
                loop.run_until_complete(red.db.set("token", token))

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
                loop.run_until_complete(red.db.set("prefix", [prefix]))

    return token


def parse_cli_flags():
    parser = argparse.ArgumentParser(description="Red - Discord Bot")
    parser.add_argument("--owner", help="ID of the owner. Only who hosts "
                                        "Red should be owner, this has "
                                        "security implications")
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

    args = parser.parse_args()

    if args.prefix:
        args.prefix = sorted(args.prefix, reverse=True)
    else:
        args.prefix = []

    return args