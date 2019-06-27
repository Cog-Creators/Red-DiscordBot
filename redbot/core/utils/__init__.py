import os
import shutil
from itertools import chain
from pathlib import Path

from .chat_formatting import box
from .tasks import *
from .fuzzy import *


# Benchmarked to be the fastest method.
def deduplicate_iterables(*iterables):
    """
    Returns a list of all unique items in ``iterables``, in the order they
    were first encountered.
    """
    # dict insertion order is guaranteed to be preserved in 3.6+
    return list(dict.fromkeys(chain.from_iterable(iterables)))


def safe_delete(pth: Path):
    if pth.exists():
        for root, dirs, files in os.walk(str(pth)):
            os.chmod(root, 0o755)

            for d in dirs:
                os.chmod(os.path.join(root, d), 0o755)

            for f in files:
                os.chmod(os.path.join(root, f), 0o755)

        shutil.rmtree(str(pth), ignore_errors=True)
