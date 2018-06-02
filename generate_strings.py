#!/usr/bin/env python3
import subprocess
import os
import sys


def main():
    interpreter = sys.executable
    print(interpreter)
    root_dir = os.getcwd()
    cogs = [i for i in os.listdir("redbot/cogs") if os.path.isdir(os.path.join("redbot/cogs", i))]
    for d in cogs:
        if "locales" in os.listdir(os.path.join("redbot/cogs", d)):
            os.chdir(os.path.join("redbot/cogs", d, "locales"))
            if "regen_messages.py" not in os.listdir(os.getcwd()):
                print(
                    f"Directory 'locales' exists for {d} but no 'regen_messages.py' is available!"
                )
                return 1
            else:
                print("Running 'regen_messages.py' for {}".format(d))
                retval = subprocess.run([interpreter, "regen_messages.py"])
                if retval.returncode != 0:
                    return 1
                os.chdir(root_dir)
    os.chdir("redbot/core/locales")
    print("Running 'regen_messages.py' for core")
    retval = subprocess.run([interpreter, "regen_messages.py"])
    if retval.returncode != 0:
        return 1
    os.chdir(root_dir)
    subprocess.run(["crowdin", "upload"])
    return 0


if __name__ == "__main__":
    sys.exit(main())
