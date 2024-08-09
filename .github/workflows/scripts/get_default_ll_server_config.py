import sys

import yaml

from redbot.cogs.audio.manager import ll_server_config


def main() -> int:
    try:
        output_file = sys.argv[1]
    except IndexError:
        print("Usage:", sys.argv[0], "<output_file>", file=sys.stderr)
        return 2

    server_config = ll_server_config.get_default_server_config()
    with open(output_file, "w", encoding="utf-8") as fp:
        yaml.safe_dump(server_config, fp)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
