#!/usr/bin/env python
import sys
import subprocess
import tempfile
import textwrap
import venv
from pathlib import Path
from typing import Sequence, Iterable, Dict

import packaging.requirements
import setuptools.config

THIS_DIRECTORY = Path(__file__).parent
REQUIREMENTS_INI_PTH: Path = THIS_DIRECTORY / "requirements.ini"

PIP_INSTALL_ARGS = ("install", "--upgrade", "--no-cache-dir")
PIP_FREEZE_ARGS = ("freeze", "--no-color")


def main() -> int:
    if not REQUIREMENTS_INI_PTH.is_file():
        print("No requirements.ini found in the same directory as this script", file=sys.stderr)
        return 1

    req_cfg = setuptools.config.read_configuration(str(REQUIREMENTS_INI_PTH))

    print("[options]")
    print("install_requires =")
    core_loose_reqs = req_cfg["options"]["install_requires"]
    full_core_reqs = get_full_reqs(core_loose_reqs)
    print(textwrap.indent("\n".join(map(str, full_core_reqs)), " " * 4))
    print()

    print("[options.extras_require]")
    for extra, extra_loose_reqs in req_cfg["options"]["extras_require"].items():
        print(extra, "=")
        full_extra_reqs = get_full_reqs(
            extra_loose_reqs, core_reqs={r.name.lower(): r for r in full_core_reqs}
        )
        print(textwrap.indent("\n".join(map(str, full_extra_reqs)), " " * 4))

    return 0


def get_full_reqs(
    loose_reqs: Iterable[str], core_reqs: Dict[str, packaging.requirements.Requirement] = ()
) -> Sequence[packaging.requirements.Requirement]:
    req_objs = {r.name.lower(): r for r in map(packaging.requirements.Requirement, loose_reqs)}
    with tempfile.TemporaryDirectory() as tmpdir:
        venv.create(tmpdir, system_site_packages=False, clear=True, with_pip=True)
        tmpdir_pth = Path(tmpdir)

        pip_exe_pth = tmpdir_pth / "bin" / "pip"

        # Upgrade pip to latest version
        proc = subprocess.Popen((pip_exe_pth, *PIP_INSTALL_ARGS, "pip"), stdout=subprocess.DEVNULL)
        proc.wait()

        # Install the loose requirements
        proc = subprocess.Popen(
            (pip_exe_pth, *PIP_INSTALL_ARGS, *map(str, req_objs.values())),
            stdout=subprocess.DEVNULL,
        )
        proc.wait()

        # Get the output of pip freeze
        proc = subprocess.Popen((pip_exe_pth, *PIP_FREEZE_ARGS), stdout=subprocess.PIPE)
        stdout = proc.communicate()[0].decode("utf-8")

        # Return Requirement objects
        ret = []
        for req_obj in map(packaging.requirements.Requirement, stdout.strip().split("\n")):
            req_name = req_obj.name.lower()
            # Don't include excluded requirements
            if req_name in core_reqs:
                if req_obj.specifier != core_reqs[req_name].specifier:
                    print(
                        f"[WARNING] {req_name} is listed as both a core requirement and an extra "
                        f"requirement, and it's possible that their versions conflict!",
                        file=sys.stderr,
                    )
                continue

            # Preserve markers
            if req_name in req_objs:
                req_obj.marker = req_objs[req_name].marker

            ret.append(req_obj)

        return ret


if __name__ == "__main__":
    sys.exit(main())
