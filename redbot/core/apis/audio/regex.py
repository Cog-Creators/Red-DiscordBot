from __future__ import annotations

import re

from typing import Final, Pattern

__all__ = [
    "YOUTUBE_ID",
    "YOUTUBE_TIMESTAMP",
    "YOUTUBE_LIST_PLAYLIST",
    "YOUTUBE_INDEX",
    "SPOTIFY_TIMESTAMP",
    "SPOTIFY_URL",
    "SOUNDCLOUD_TIMESTAMP",
    "TWITCH_TIMESTAMP",
    "ICYCAST_STREAM_TITLE",
    "REMOVE_START",
    "SQUARE",
    "MENTION",
    "FAILED_CONVERSION",
    "TIME_CONVERTER",
    "LAVALINK_READY_LINE",
    "LAVALINK_FAILED_TO_START",
    "LAVALINK_BUILD_LINE",
    "LAVALINK_LAVAPLAYER_LINE",
    "LAVALINK_JAVA_LINE",
    "LAVALINK_BRANCH_LINE",
    "LAVALINK_BUILD_TIME_LINE",
    "JAVA_VERSION_LINE",
    "JAVA_SHORT_VERSION",
    "CURLY_BRACKETS",
]


YOUTUBE_ID: Final[Pattern] = re.compile(r"^[a-zA-Z0-9_-]{11}$")
YOUTUBE_TIMESTAMP: Final[Pattern] = re.compile(r"[&|?]t=(\d+)s?")
YOUTUBE_LIST_PLAYLIST: Final[Pattern] = re.compile(
    r"^(https?://)?(www\.)?(youtube\.com|youtu\.?be)(/playlist\?).*(list=)(.*)(&|$)"
)
YOUTUBE_INDEX: Final[Pattern] = re.compile(r"&index=(\d+)")

SPOTIFY_TIMESTAMP: Final[Pattern] = re.compile(r"#(\d+):(\d+)")
SPOTIFY_URL: Final[Pattern] = re.compile(r"(http[s]?://)?(open.spotify.com)/")

SOUNDCLOUD_TIMESTAMP: Final[Pattern] = re.compile(r"#t=(\d+):(\d+)s?")

TWITCH_TIMESTAMP: Final[Pattern] = re.compile(r"\?t=(\d+)h(\d+)m(\d+)s")

ICYCAST_STREAM_TITLE: Final[Pattern] = re.compile(br"StreamTitle='([^']*)';")


REMOVE_START: Final[Pattern] = re.compile(r"^(sc|list) ")

SQUARE = re.compile(r"[\[\]]")
MENTION: Final[Pattern] = re.compile(r"^<?(?:(?:@[!&]?)?|#)(\d{15,21})>?$")

FAILED_CONVERSION: Final[Pattern] = re.compile('Converting to "(.*)" failed for parameter "(.*)".')
TIME_CONVERTER: Final[Pattern] = re.compile(r"(?:(\d+):)?([0-5]?[0-9]):([0-5][0-9])")

LAVALINK_READY_LINE: Final[Pattern] = re.compile(rb"Started Launcher in \S+ seconds")
LAVALINK_FAILED_TO_START: Final[Pattern] = re.compile(rb"Web server failed to start. (.*)")
LAVALINK_BUILD_LINE: Final[Pattern] = re.compile(rb"Build time:\s+(?P<build_time>\d+[.\d+]*)")
LAVALINK_LAVAPLAYER_LINE: Final[Pattern] = re.compile(rb"Lavaplayer\s+(?P<lavaplayer>\d+[.\d+]*)")
LAVALINK_JAVA_LINE: Final[Pattern] = re.compile(rb"JVM:\s+(?P<jvm>\d+[.\d+]*)")
LAVALINK_BRANCH_LINE: Final[Pattern] = re.compile(rb"Branch\s+(?P<branch>[\w\-\d_.]+)")
LAVALINK_BUILD_TIME_LINE: Final[Pattern] = re.compile(rb"Build time:\s+(?P<build_time>\d+[.\d+]*)")


JAVA_VERSION_LINE: Final[Pattern] = re.compile(
    r'version "(?P<major>\d+).(?P<minor>\d+).\d+(?:_\d+)?(?:-[A-Za-z0-9]+)?"'
)
JAVA_SHORT_VERSION: Final[Pattern] = re.compile(r'version "(?P<major>\d+)"')

CURLY_BRACKETS: Final[Pattern] = re.compile(r"[{}]")
