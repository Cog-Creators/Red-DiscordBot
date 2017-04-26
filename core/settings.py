import argparse

# Do we even need a Settings class this time? To be decided


class Settings:
    def __init__(self):
        args = {}
        self.coowners = []

    def can_login(self):
        """Used on start to determine if Red is setup enough to login"""
        raise NotImplementedError


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