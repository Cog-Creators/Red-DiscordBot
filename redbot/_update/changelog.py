import dataclasses
import datetime
import functools
import os
import re
from typing import Dict, List

import aiohttp
import yarl
from packaging.version import Version


_CHANGELOG_PATTERN = re.compile(
    r"\n<!--+ +RED-CHANGELOG-BEGIN: (?P<version>.+) +--+>\n"
    r"(?P<content>[\s\S]+?)"
    r"\n<!--+ +RED-CHANGELOG-END +--+>"
)
_RTD_CANONICAL_URL = os.getenv("_RED_RTD_CANONICAL_URL") or "https://docs.discord.red/en/stable/"


@dataclasses.dataclass
class VersionChangelog:
    version: Version
    content: str
    _RELEASE_DATE_PATTERN = re.compile(
        r"^<!--+ +RED-CHANGELOG-RELEASE-DATE: (\d{4})-(\d{2})-(\d{2}) +--+>$",
        re.MULTILINE,
    )
    _CONTRIBUTORS_PATTERN = re.compile(
        r"^<!--+ +RED-CHANGELOG-CONTRIBUTORS: (?P<contributors>.+) +--+>$",
        re.MULTILINE,
    )
    _READ_BEFORE_UPDATING_SECTION_PATTERN = re.compile(
        r"\n<!--+ +RED-CHANGELOG-READ-BEFORE-UPDATE-BEGIN +--+>\n"
        r"(?P<content>[\s\S]+?)"
        r"\n<!--+ +RED-CHANGELOG-READ-BEFORE-UPDATE-END +--+>"
    )
    _USER_CHANGELOG_SECTION_PATTERN = re.compile(
        r"\n<!--+ +RED-CHANGELOG-USER-CHANGELOG-BEGIN +--+>\n"
        r"(?P<content>[\s\S]+?)"
        r"\n<!--+ +RED-CHANGELOG-USER-CHANGELOG-END +--+>"
    )

    @functools.cached_property
    def release_date(self) -> datetime.date:
        return datetime.date(*map(int, self._RELEASE_DATE_PATTERN.search(self.content).groups()))

    @functools.cached_property
    def contributors(self) -> List[str]:
        match = self._CONTRIBUTORS_PATTERN.search(self.content)
        if match is None:
            return []
        return match["contributors"].split()

    @functools.cached_property
    def read_before_updating_section(self) -> str:
        return "\n".join(
            match["content"].strip()
            for match in self._READ_BEFORE_UPDATING_SECTION_PATTERN.finditer(self.content)
        )

    @functools.cached_property
    def user_changelog_section(self) -> str:
        return "\n".join(
            match["content"].strip()
            for match in self._USER_CHANGELOG_SECTION_PATTERN.finditer(self.content)
        )


_Changelogs = Dict[Version, VersionChangelog]


def parse_changelogs(content: str) -> _Changelogs:
    changelogs = {}
    for match in _CHANGELOG_PATTERN.finditer(content):
        changelog = VersionChangelog(Version(match["version"]), match["content"])
        changelogs[changelog.version] = changelog

    return changelogs


def render_markdown(changelogs: _Changelogs, *, minimal: bool = False) -> str:
    if not changelogs:
        return ""

    parts = []
    contributors = sorted(
        {
            contributor
            for changelog in changelogs.values()
            for contributor in changelog.contributors
        }
    )
    if contributors:
        contributor_thanks = (
            "# Thanks to our contributors \N{HEAVY BLACK HEART}\N{VARIATION SELECTOR-16}\n"
            "**The releases below were made with help from the following people:**  \n"
        )
        contributor_thanks += ", ".join(
            f"[@{contributor}](https://github.com/sponsors/{contributor})"
            for contributor in contributors
        )
        parts.append(contributor_thanks)

    parts.append("# Read before updating")
    for changelog in reversed(changelogs.values()):
        if changelog.read_before_updating_section:
            parts.append(f"## {changelog.version}")
            parts.append(changelog.read_before_updating_section)

    parts.append("# User changelog")
    for changelog in reversed(changelogs.values()):
        if changelog.user_changelog_section:
            parts.append(f"## {changelog.version}")
            parts.append(changelog.user_changelog_section)

    return "\n".join(parts)


def get_changelogs_newer_than(changelogs: _Changelogs, version: Version) -> _Changelogs:
    return {
        changelog_version: changelog
        for changelog_version, changelog in changelogs.items()
        if changelog_version > version
    }


async def fetch_changelogs() -> _Changelogs:
    """
    Fetch the Markdown-formatted changelog from Red's docs site.

    Returns
    -------
    Dict[Version, VersionChangelog]
        A dict mapping versions to their changelogs. Sorted by version, newest first.
    """
    async with aiohttp.ClientSession(raise_for_status=True) as session:
        async with session.get(yarl.URL(_RTD_CANONICAL_URL) / "_markdown/changelog.md") as resp:
            return parse_changelogs(await resp.text())
