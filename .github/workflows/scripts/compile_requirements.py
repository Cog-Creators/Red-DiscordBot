import os
import shutil
import subprocess
import sys
from pathlib import Path


GITHUB_OUTPUT = os.environ["GITHUB_OUTPUT"]
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
            "--resolver=backtracking",
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

with open(GITHUB_OUTPUT, "a", encoding="utf-8") as fp:
    fp.write(f"sys_platform={sys.platform}\n")
