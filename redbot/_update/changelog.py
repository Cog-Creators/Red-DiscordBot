import dataclasses
import datetime
import functools
import os
import re
from typing import Any, Dict, List

import aiohttp
import yarl
from packaging.version import Version
from typing_extensions import Self


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

    @classmethod
    def from_json_dict(cls, data: Dict[str, Any]) -> Self:
        return cls(version=Version(data["version"]), content=data["content"])

    def to_json_dict(self) -> Dict[str, Any]:
        return {"version": str(self.version), "content": self.content}

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


Changelogs = Dict[Version, VersionChangelog]


def parse_changelogs(content: str) -> Changelogs:
    changelogs = {}
    for match in _CHANGELOG_PATTERN.finditer(content):
        changelog = VersionChangelog(Version(match["version"]), match["content"])
        changelogs[changelog.version] = changelog

    return changelogs


def render_markdown(changelogs: Changelogs, *, minimal: bool = False) -> str:
    if not changelogs:
        return ""

    parts = ["# Read before updating"]
    for changelog in reversed(changelogs.values()):
        parts.append(f"## {changelog.version}")
        parts.append(changelog.read_before_updating_section)

    contributors = sorted(
        {
            contributor
            for changelog in changelogs.values()
            for contributor in changelog.contributors
        }
    )
    if contributors:
        contributor_thanks = (
            "  \n**The releases below were made with help from the following people:**  \n"
        )
        contributor_thanks += ", ".join(
            f"[@{contributor}](https://github.com/sponsors/{contributor})"
            for contributor in contributors
        )
        contributor_thanks += "  \n**Thank you** \N{HEAVY BLACK HEART}\N{VARIATION SELECTOR-16}"
        parts.append(contributor_thanks)

    # show the header both at the top and the bottom
    parts.append(parts[0])

    return "\n".join(parts)


def get_changelogs_between(
    changelogs: Changelogs, newer_than: Version, not_newer_than: Version
) -> Changelogs:
    return {
        changelog_version: changelog
        for changelog_version, changelog in changelogs.items()
        if newer_than < changelog_version <= not_newer_than
    }


async def fetch_changelogs() -> Changelogs:
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
