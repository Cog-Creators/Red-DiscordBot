import os
import shutil
import subprocess
import sys
from pathlib import Path


REQUIREMENTS_FOLDER = Path(__file__).parents[3].absolute() / "requirements"
os.chdir(REQUIREMENTS_FOLDER)


def pip_compile(name: str) -> None:
    subprocess.check_call(
        (
            sys.executable,
            "-m",
            "piptools",
            "compile",
            "--upgrade",
            "--verbose",
            f"{name}.in",
            "--output-file",
            f"{sys.platform}-{name}.txt",
        )
    )


pip_compile("base")
shutil.copyfile(f"{sys.platform}-base.txt", "base.txt")
for file in REQUIREMENTS_FOLDER.glob("extra-*.in"):
    pip_compile(file.stem)

print(f"::set-output name=sys_platform::{sys.platform}")
