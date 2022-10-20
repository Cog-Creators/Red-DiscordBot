import importlib.metadata
import pkg_resources
import os
import sys

import pytest

from redbot import core
from redbot.core import VersionInfo


def test_version_working():
    assert hasattr(core, "__version__")
    assert core.__version__[0] == "3"


# When adding more of these, ensure they are added in ascending order of precedence
version_tests = (
    "3.0.0a32.post10.dev12",
    "3.0.0rc1.dev1",
    "3.0.0rc1",
    "3.0.0",
    "3.0.1.dev1",
    "3.0.1.dev2+gdbaf31e",
    "3.0.1.dev2+gdbaf31e.dirty",
    "3.0.1.dev3+gae98d77",
    "3.0.1",
    "3.0.1.post1.dev1",
    "3.0.1.post1",
    "2018.10.6b21",
)


def test_version_info_str_parsing():
    for version_str in version_tests:
        assert version_str == str(VersionInfo.from_str(version_str))


def test_version_info_lt():
    for next_idx, cur in enumerate(version_tests[:-1], start=1):
        cur_test = VersionInfo.from_str(cur)
        next_test = VersionInfo.from_str(version_tests[next_idx])
        assert cur_test < next_test


def test_version_info_gt():
    assert VersionInfo.from_str(version_tests[1]) > VersionInfo.from_str(version_tests[0])


def test_python_version_has_lower_bound():
    """
    Due to constant issues in support with Red being installed on a Python version that was not
    supported by any Red version, it is important that we have both an upper and lower bound set.
    """
    requires_python = importlib.metadata.metadata("Red-DiscordBot")["Requires-Python"]
    assert requires_python is not None

    # `pkg_resources` needs a regular requirement string, so "x" serves as requirement's name here
    req = pkg_resources.Requirement.parse(f"x{requires_python}")
    assert any(op in (">", ">=") for op, version in req.specs)


@pytest.mark.skipif(
    os.getenv("TOX_RED", False) and sys.version_info >= (3, 10),
    reason="Testing on yet to be supported Python version.",
)
def test_python_version_has_upper_bound():
    """
    Due to constant issues in support with Red being installed on a Python version that was not
    supported by any Red version, it is important that we have both an upper and lower bound set.
    """
    requires_python = importlib.metadata.metadata("Red-DiscordBot")["Requires-Python"]
    assert requires_python is not None

    # `pkg_resources` needs a regular requirement string, so "x" serves as requirement's name here
    req = pkg_resources.Requirement.parse(f"x{requires_python}")
    assert any(op in ("<", "<=") for op, version in req.specs)
