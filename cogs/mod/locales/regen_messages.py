import subprocess
import os
import sys

TO_TRANSLATE = [
    os.path.join("..", "cleanup.py"),
    os.path.join("..", "filter.py"),
    os.path.join("..", "mod.py")
]


def regen_messages():
    subprocess.run(
        [sys.executable, 'pygettext.py', '-n'] + TO_TRANSLATE
    )


if __name__ == "__main__":
    regen_messages()
