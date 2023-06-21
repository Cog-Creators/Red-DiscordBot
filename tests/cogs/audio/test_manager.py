import itertools

import pytest

from redbot.cogs.audio.manager import LavalinkOldVersion, LavalinkVersion


ORDERED_VERSIONS = [
    LavalinkOldVersion("3.3.2.3", build_number=1239),
    LavalinkOldVersion("3.4.0", build_number=1275),
    LavalinkOldVersion("3.4.0", build_number=1350),
    # LavalinkVersion is always newer than LavalinkOldVersion
    LavalinkVersion(3, 3),
    LavalinkVersion(3, 4),
    LavalinkVersion(3, 5, rc=1),
    LavalinkVersion(3, 5, rc=2),
    LavalinkVersion(3, 5, rc=3),
    # version with `+red.N` build number is newer than an equivalent upstream version
    LavalinkVersion(3, 5, rc=3, red=1),
    LavalinkVersion(3, 5, rc=3, red=2),
    # all RC versions (including ones with `+red.N`) are older than a stable version
    LavalinkVersion(3, 5),
    # version with `+red.N` build number is newer than an equivalent upstream version
    LavalinkVersion(3, 5, red=1),
    LavalinkVersion(3, 5, red=2),
    # but newer version number without `+red.N` is still newer
    LavalinkVersion(3, 5, 1),
]


@pytest.mark.parametrize(
    "raw_version,raw_build_number,expected",
    (
        # 3-segment version number
        ("3.4.0", "1350", LavalinkOldVersion("3.4.0", build_number=1350)),
        # 4-segment version number
        ("3.3.2.3", "1239", LavalinkOldVersion("3.3.2.3", build_number=1239)),
        # 3-segment version number with 3-digit build number
        ("3.3.1", "987", LavalinkOldVersion("3.3.1", build_number=987)),
    ),
)
def test_old_ll_version_parsing(
    raw_version: str, raw_build_number: str, expected: LavalinkOldVersion
) -> None:
    line = b"Version: %b\nBuild: %b" % (raw_version.encode(), raw_build_number.encode())
    assert LavalinkOldVersion.from_version_output(line)


@pytest.mark.parametrize(
    "raw_version,expected",
    (
        # older version format that allowed stripped `.0` and no dot in `rc.4`, used until LL 3.6
        ("3.5-rc4", LavalinkVersion(3, 5, rc=4)),
        ("3.5", LavalinkVersion(3, 5)),
        # newer version format
        ("3.6.0-rc.1", LavalinkVersion(3, 6, 0, rc=1)),
        # downstream RC version with `+red.N` suffix
        ("3.7.5-rc.1+red.1", LavalinkVersion(3, 7, 5, rc=1, red=1)),
        ("3.7.5-rc.1+red.123", LavalinkVersion(3, 7, 5, rc=1, red=123)),
        # upstream stable version
        ("3.7.5", LavalinkVersion(3, 7, 5)),
        # downstream stable version with `+red.N` suffix
        ("3.7.5+red.1", LavalinkVersion(3, 7, 5, red=1)),
        ("3.7.5+red.123", LavalinkVersion(3, 7, 5, red=123)),
    ),
)
def test_ll_version_parsing(raw_version: str, expected: LavalinkVersion) -> None:
    line = b"Version: " + raw_version.encode()
    assert LavalinkVersion.from_version_output(line)


def test_ll_version_comparison() -> None:
    it1, it2 = itertools.tee(ORDERED_VERSIONS)
    next(it2, None)
    for a, b in zip(it1, it2):
        assert a < b
