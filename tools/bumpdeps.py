#!/usr/bin/env python3.7


"""Script to bump pinned dependencies in setup.cfg.

This script aims to help update our list of pinned primary and
secondary dependencies in *setup.cfg*, using the unpinned primary
dependencies listed in *primary_deps.ini*.

This script will not work when run on Windows.

What this script does
---------------------
It prints to stdout all primary and secondary dependencies for Red,
pinned to the latest possible version, within the constraints specified
in ``primary_deps.ini``. The output should be suitable for copying and
pasting into ``setup.cfg``. PEP 508 markers are preserved.

How this script works
---------------------
Overview:
1. Primary dependencies are read from primary_deps.ini using
setuptools' config parser.
2. A clean virtual environment is created in a temporary directory.
3. Core primary dependencies are passed to the ``pip install`` command
for that virtual environment.
4. Pinned primary dependencies are obtained by reading the output of
``pip freeze`` in that virtual environment, and any PEP 508 markers
shown with the requirement in ``primary_deps.ini`` are preserved.
5. Steps 2-4 are repeated for each extra requirement, but care is taken
not to duplicate core dependencies (primary or secondary) in the final
pinned extra dependencies.

This script makes use of the *packaging* library to parse version
specifiers and environment markers.

Known Limitations
-----------------
These limitations don't stop this script from being helpful, but
hopefully help explain in which situations some dependencies may need
to be listed manually in ``setup.cfg``.

1. Whilst environment markers of any primary dependencies specified in
``primary_deps.ini`` are preserved in the output, they will not be
added to secondary dependencies. So for example, if some package
*dep1* has a dependency *dep2*, and *dep1* is listed as a primary
dependency in ``primary_deps.ini`` like follows::
    dep1; sys_platform == "linux"

Then the output will look like this::
    dep1==1.1.1; sys_platform == "linux"
    dep2==2.2.2

So even though ``dep1`` and its dependencies should only be installed on
Linux, in reality, its dependencies will be installed regardless. To
work around this, simply list the secondary dependencies in
``primary_deps.ini`` as well, with the environment markers.

2. If a core requirement and an extra requirement have a common
sub-dependency, there is a chance the sub-dependency will have a version
conflict unless it is manually held back. This script will issue a
warning to stderr when it thinks this might be happening.

3. Environment markers which exclude dependencies from the system
running this script will cause those dependencies to be excluded from
the output. So for example, if a dependency has the environment marker
``sys_platform == "darwin"``, and the script is being run on linux, then
this dependency will be ignored, and must be added to ``setup.cfg``
manually.
"""


import shlex
import subprocess as sp
import sys
import tempfile
import textwrap
import venv

from pathlib import Path
from typing import Dict, Iterable, Sequence

import packaging.requirements
import setuptools.config

THIS_DIRECTORY = Path(__file__).parent
REQUIREMENTS_INI_PTH: Path = THIS_DIRECTORY / "primary_deps.ini"

PIP_INSTALL_ARGS = ("install", "--upgrade")
PIP_FREEZE_ARGS = ("freeze", "--no-color")


def main() -> int:
    if not REQUIREMENTS_INI_PTH.is_file():
        print("No primary_deps.ini found in the same directory as bumpdeps.py", file=sys.stderr)
        return 1

    primary_reqs_cfg = setuptools.config.read_configuration(str(REQUIREMENTS_INI_PTH))

    print("[options]")
    print("install_requires =")
    core_primary_deps = primary_reqs_cfg["options"]["install_requires"]
    full_core_reqs = get_all_reqs(core_primary_deps)
    print(textwrap.indent("\n".join(map(str, full_core_reqs)), " " * 4))
    print()

    print("[options.extras_require]")
    for (extra, extra_primary_deps) in primary_reqs_cfg["options"]["extras_require"].items():
        print(extra, "=")
        full_extra_reqs = get_all_reqs(
            extra_primary_deps, all_core_deps={r.name.lower(): r for r in full_core_reqs}
        )
        print(textwrap.indent("\n".join(map(str, full_extra_reqs)), " " * 4))

    return 0


def get_all_reqs(
    primary_deps: Iterable[str], all_core_deps: Dict[str, packaging.requirements.Requirement] = ()
) -> Sequence[packaging.requirements.Requirement]:
    reqs_dict = {r.name.lower(): r for r in map(packaging.requirements.Requirement, primary_deps)}
    with tempfile.TemporaryDirectory() as tmpdir:
        venv.create(tmpdir, system_site_packages=False, clear=True, with_pip=True)
        tmpdir_pth = Path(tmpdir)

        pip_exe_pth = tmpdir_pth / "bin" / "pip"

        # Upgrade pip to latest version
        sp.run((pip_exe_pth, *PIP_INSTALL_ARGS, "pip"), stdout=sp.DEVNULL, check=True)

        # Install the primary dependencies
        sp.run(
            (pip_exe_pth, *PIP_INSTALL_ARGS, *map(str, reqs_dict.values())),
            stdout=sp.DEVNULL,
            check=True,
        )

        # Get pinned primary+secondary dependencies from pip freeze
        proc = sp.run(
            (pip_exe_pth, *PIP_FREEZE_ARGS), stdout=sp.PIPE, check=True, encoding="utf-8"
        )

        # Return Requirement objects
        ret = []
        for req_obj in map(packaging.requirements.Requirement, proc.stdout.strip().split("\n")):
            dep_name = req_obj.name.lower()
            # Don't include core dependencies if these are extra dependencies
            if dep_name in all_core_deps:
                if req_obj.specifier != all_core_deps[dep_name].specifier:
                    print(
                        f"[WARNING] {dep_name} is listed as both a core requirement and an extra "
                        f"requirement, and it's possible that their versions conflict!",
                        file=sys.stderr,
                    )
                continue

            # Preserve environment markers
            if dep_name in reqs_dict:
                req_obj.marker = reqs_dict[dep_name].marker

            ret.append(req_obj)

        return ret


if __name__ == "__main__":
    try:
        exit_code = main()
    except sp.CalledProcessError as exc:
        cmd = " ".join(map(lambda c: shlex.quote(str(c)), exc.cmd))
        print(
            f"The following command failed with code {exc.returncode}:\n    ", cmd, file=sys.stderr
        )
        exit_code = 1

    sys.exit(exit_code)
