#!/usr/bin/env python3
import redgettext
import subprocess
import sys


def main():
    args = ["--command-docstrings", "--verbose", "--recursive", "redbot"]
    print(f"Running command `redgettext {' '.join(args)}`")
    returncode = redgettext.main(args)
    print(f"redgettext exited with code {returncode}")
    if returncode != 0:
        return returncode

    args = ["crowdin", "upload"]
    print(f"Running command `{' '.join(args)}`")
    proc = subprocess.run(args)
    print(f"crowdin exited with code {proc.returncode}")
    return proc.returncode


if __name__ == "__main__":
    sys.exit(main())
