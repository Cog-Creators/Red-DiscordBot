from __future__ import annotations

from typing import Final

__all__ = [
    "SET_temp_store",
    "SET_journal_mode",
    "SET_read_uncommitted",
    "FETCH_user_version",
    "SET_user_version",
]


SET_temp_store: Final[
    str
] = """
PRAGMA
    temp_store = 2
;
"""
SET_journal_mode: Final[
    str
] = """
PRAGMA
    journal_mode = wal
;
"""
SET_read_uncommitted: Final[
    str
] = """
PRAGMA
    read_uncommitted = 1
;
"""
FETCH_user_version: Final[
    str
] = """
PRAGMA
    user_version
;
"""
SET_user_version: Final[
    str
] = """
PRAGMA
    user_version = 3
;
"""
