import redbot
import re
import sys

DEBIAN_PACKAGE_VERSION_RE = re.compile(r"(?:Standards-Version: )(?P<version>(\d\.?){3,}\w*)")


def check_version_number():
    file_path = "debian/control"
    version = redbot.__version__
    with open(file_path, "r") as control_file:
        content = control_file.read()
    for line in content.splitlines():
        match = DEBIAN_PACKAGE_VERSION_RE.match(line)
        if not match:
            continue
        if version != match.group("version"):
            print("The version number in debian/control doesn't match redbot's version.")
            print('Please fix the line "Standards-Version". You can use "make updatedebian".')
            print("Cancelling build...")
            sys.exit(1)
        else:
            print("Version OK.")
            sys.exit(0)
    print("Incorrect format in debian/control.")
    sys.exit(1)


def update_version_number():
    file_path = "debian/control"
    version = redbot.__version__
    with open(file_path, "r", newline="") as control_file:
        content = control_file.read()
    for line in content.splitlines():
        match = DEBIAN_PACKAGE_VERSION_RE.match(line)
        if not match:
            continue
        if version != match.group("version"):
            content = content.replace(line, f"Standards-Version: {version}")
            with open(file_path, "w", newline="") as control_file:
                control_file.write(content)
            print("Version number updated!")


if __name__ == "__main__":
    if "--update" in sys.argv:
        update_version_number()
    else:
        check_version_number()
