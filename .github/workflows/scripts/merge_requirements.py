import os
from pathlib import Path
from packaging.markers import Marker
from packaging.requirements import Requirement


REQUIREMENTS_FOLDER = Path(__file__).parents[3].absolute() / "requirements"
os.chdir(REQUIREMENTS_FOLDER)


def get_requirements(fp):
    return [
        Requirement(line)
        for line in fp.read().splitlines()
        if line and not line.startswith(("#", " "))
    ]


names = ["base"]
names.extend(file.stem for file in REQUIREMENTS_FOLDER.glob("extra-*.in"))
base_requirements = []

for name in names:
    # {req_name: {sys_platform: Requirement}
    input_data = {}
    all_platforms = set()
    for file in REQUIREMENTS_FOLDER.glob(f"*-{name}.txt"):
        platform_name = file.stem.split("-", maxsplit=1)[0]
        all_platforms.add(platform_name)
        with file.open(encoding="utf-8") as fp:
            requirements = get_requirements(fp)

        for req in requirements:
            platforms = input_data.setdefault(req.name, {})
            platforms[platform_name] = req

    output = base_requirements if name == "base" else []
    for req_name, platforms in input_data.items():
        req = next(iter(platforms.values()))
        if not all(value == req for value in platforms.values()):
            raise RuntimeError(f"Incompatible requirements for {req_name}.")

        base_req = next(
            (base_req for base_req in base_requirements if base_req.name == req.name), None
        )
        if base_req is not None:
            old_base_marker = base_req.marker
            old_req_marker = req.marker
            req.marker = base_req.marker = None
            if base_req != req:
                raise RuntimeError(f"Incompatible requirements for {req_name}.")

            base_req.marker = old_base_marker
            req.marker = old_req_marker
            if base_req.marker is None or base_req.marker == req.marker:
                continue

        if len(platforms) == len(all_platforms):
            output.append(req)
            continue
        elif len(platforms) < len(all_platforms - platforms.keys()):
            platform_marker = " or ".join(
                f"sys_platform == '{platform}'" for platform in platforms
            )
        else:
            platform_marker = " and ".join(
                f"sys_platform != '{platform}'" for platform in all_platforms - platforms.keys()
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
            fp.write(str(req))
            fp.write("\n")
