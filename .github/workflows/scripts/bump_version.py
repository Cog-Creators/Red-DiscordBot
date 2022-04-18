import os
import re
import sys
from typing import Match

import redbot


if int(os.environ.get("JUST_RETURN_VERSION", 0)):
    print(f"::set-output name=version::{redbot._VERSION}")
    sys.exit(0)


version_info = None


def repl(match: Match[str]) -> str:
    global version_info

    print(f"::set-output name=old_version::{match.group('version')}")

    new_stable_version = os.environ.get("NEW_STABLE_VERSION", "auto")
    if new_stable_version == "auto":
        version_info = redbot.VersionInfo.from_str(match.group("version"))
        version_info.dev_release = None
    else:
        version_info = redbot.VersionInfo.from_str(new_stable_version)

    if int(os.environ.get("DEV_BUMP", 0)):
        version_info.micro += 1
        version_info.dev_release = 1

    return f'_VERSION = "{version_info}"'


with open("redbot/__init__.py", encoding="utf-8") as fp:
    new_contents, found = re.subn(
        pattern=r'^_VERSION = "(?P<version>[^"]*)"$',
        repl=repl,
        string=fp.read(),
        count=1,
        flags=re.MULTILINE,
    )

if not found:
    print("Couldn't find `_VERSION` line!")
    sys.exit(1)

with open("redbot/__init__.py", "w", encoding="utf-8", newline="\n") as fp:
    fp.write(new_contents)

print(f"::set-output name=new_version::{version_info}")
