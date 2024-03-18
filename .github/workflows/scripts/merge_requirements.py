from __future__ import annotations

import os
from pathlib import Path
from typing import List, TextIO

from packaging.markers import Marker
from packaging.requirements import Requirement


REQUIREMENTS_FOLDER = Path(__file__).parents[3].absolute() / "requirements"
os.chdir(REQUIREMENTS_FOLDER)


class RequirementData:
    def __init__(self, requirement_string: str) -> None:
        self.req = Requirement(requirement_string)
        self.comments = set()

    def __hash__(self) -> int:
        return hash(self.req)

    def __eq__(self, other: RequirementData) -> bool:
        return self.req == other.req

    @property
    def name(self) -> str:
        return self.req.name

    @property
    def marker(self) -> Marker:
        return self.req.marker

    @marker.setter
    def marker(self, value: Marker) -> None:
        self.req.marker = value


def get_requirements(fp: TextIO) -> List[RequirementData]:
    requirements = []

    current = None
    for line in fp.read().splitlines():
        annotation_prefix = "    # "
        if line.startswith(annotation_prefix) and current is not None:
            source = line[len(annotation_prefix) :].strip()
            if source == "via":
                continue
            via_prefix = "via "
            if source.startswith(via_prefix):
                source = source[len(via_prefix) :]
            current.comments.add(source)
        elif line and not line.startswith(("#", " ")):
            current = RequirementData(line)
            requirements.append(current)

    return requirements


names = ["base"]
names.extend(file.stem for file in REQUIREMENTS_FOLDER.glob("extra-*.in"))
base_requirements = []

for name in names:
    # {req_data: {sys_platform: RequirementData}
    input_data = {}
    all_envs = set()
    # all_platforms = set()
    # all_python_versions = set()
    for file in REQUIREMENTS_FOLDER.glob(f"*-{name}.txt"):
        platform_name, python_version, _ = file.stem.split("-", maxsplit=2)
        env_name = f"{platform_name}-{python_version}"
        all_envs.add(env_name)
        # all_platforms.add(platform_name)
        # all_python_versions.add(python_version)
        with file.open(encoding="utf-8") as fp:
            requirements = get_requirements(fp)

        for req in requirements:
            envs = input_data.setdefault(req, {})
            envs[env_name] = req

    output = base_requirements if name == "base" else []
    for req, envs in input_data.items():
        python_versions_per_platform = {}
        platforms_per_python_version = {}
        for env_name, other_req in envs.items():
            platform_name, python_version = env_name.split("-", maxsplit=1)
            python_versions_per_platform.setdefault(platform_name, []).append(python_version)
            platforms_per_python_version.setdefault(python_version, []).append(platform_name)

            req.comments.update(other_req.comments)

        base_req = next(
            (base_req for base_req in base_requirements if base_req.name == req.name), None
        )
        if base_req is not None:
            old_base_marker = base_req.marker
            old_req_marker = req.marker
            req.marker = base_req.marker = None
            if base_req.req != req.req:
                raise RuntimeError(f"Incompatible requirements for {req.name}.")

            base_req.marker = old_base_marker
            req.marker = old_req_marker
            if base_req.marker is None or base_req.marker == req.marker:
                continue

        if len(envs) == len(all_envs):
            output.append(req)
            continue

        if len(set(map(frozenset, python_versions_per_platform.values()))) == 1:
            # same Python version set for all platforms, limit by platform only
            if len(envs) < len(all_envs - envs.keys()):
                platform_marker = " or ".join(
                    f"sys_platform == '{platform}'" for platform in envs
                )
            else:
                platform_marker = " and ".join(
                    f"sys_platform != '{platform}'" for platform in all_envs - envs.keys()
                )
        elif len(set(map(frozenset, platforms_per_python_version.values()))) == 1:
            # same platform set for all python version, limit by Python version only
            if len(envs) < len(all_envs - envs.keys()):
                platform_marker = " or ".join(
                    f"python_version == '{platform}'" for platform in envs
                )
            else:
                platform_marker = " and ".join(
                    f"python_version != '{platform}'" for platform in all_envs - envs.keys()
                )
        else:
            if len(envs) < len(all_envs - envs.keys()):
                platform_marker = " or ".join(
                    f"(sys_platform == '{platform}' and python_version == '{platform}')"
                    for platform in envs
                )
            else:
                platform_marker = " and ".join(
                    f"(sys_platform != '{platform}' and python_version != '{platform}')"
                    for platform in all_envs - envs.keys()
                )


        new_marker = (
            f"({req.marker}) and ({platform_marker})"
            if req.marker is not None
            else platform_marker
        )
        req.marker = Marker(new_marker)
        if base_req is not None and base_req.marker == req.marker:
            continue

        output.append(req)

    output.sort(key=lambda req: (req.marker is not None, req.name))
    with open(f"{name}.txt", "w+", encoding="utf-8") as fp:
        for req in output:
            fp.write(str(req.req))
            fp.write("\n")
            comments = sorted(req.comments)

            if len(comments) == 1:
                source = comments[0]
                fp.write("    # via ")
                fp.write(source)
                fp.write("\n")
            else:
                fp.write("    # via\n")
                for source in comments:
                    fp.write("    #   ")
                    fp.write(source)
                    fp.write("\n")
