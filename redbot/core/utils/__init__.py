__all__ = ["TYPE_CHECKING", "NewType", "safe_delete"]

from pathlib import Path
import os
import shutil

try:
    from typing import TYPE_CHECKING
except ImportError:
    TYPE_CHECKING = False

try:
    from typing import NewType
except ImportError:

    def NewType(name, tp):
        return type(name, (tp,), {})


def safe_delete(pth: Path):
    if pth.exists():
        for root, dirs, files in os.walk(str(pth)):
            os.chmod(root, 0o755)
            for d in dirs:
                os.chmod(os.path.join(root, d), 0o755)
            for f in files:
                os.chmod(os.path.join(root, f), 0o755)
        shutil.rmtree(str(pth), ignore_errors=True)
