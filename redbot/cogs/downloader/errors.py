from __future__ import annotations

from typing import TYPE_CHECKING, List

if TYPE_CHECKING:
    from .repo_manager import Candidate


__all__ = [
    "DownloaderException",
    "GitException",
    "InvalidRepoName",
    "CopyingError",
    "ExistingGitRepo",
    "MissingGitRepo",
    "CloningError",
    "CurrentHashError",
    "HardResetError",
    "UpdateError",
    "GitDiffError",
    "NoRemoteURL",
    "UnknownRevision",
    "AmbiguousRevision",
    "PipError",
]


class DownloaderException(Exception):
    """
    Base class for Downloader exceptions.
    """


class GitException(DownloaderException):
    """
    Generic class for git exceptions.
    """

    def __init__(self, message: str, git_command: str) -> None:
        self.git_command = git_command
        super().__init__(f"Git command failed: {git_command}\nError message: {message}")


class InvalidRepoName(DownloaderException):
    """
    Throw when a repo name is invalid. Check
    the message for a more detailed reason.
    """


class CopyingError(DownloaderException):
    """
    Throw when there was an issue
    during copying of module's files.
    """


class ExistingGitRepo(DownloaderException):
    """
    Thrown when trying to clone into a folder where a
    git repo already exists.
    """


class MissingGitRepo(DownloaderException):
    """
    Thrown when a git repo is expected to exist but
    does not.
    """


class CloningError(GitException):
    """
    Thrown when git clone returns a non zero exit code.
    """


class CurrentHashError(GitException):
    """
    Thrown when git returns a non zero exit code attempting
    to determine the current commit hash.
    """


class HardResetError(GitException):
    """
    Thrown when there is an issue trying to execute a hard reset
    (usually prior to a repo update).
    """


class UpdateError(GitException):
    """
    Thrown when git pull returns a non zero error code.
    """


class GitDiffError(GitException):
    """
    Thrown when a git diff fails.
    """


class NoRemoteURL(GitException):
    """
    Thrown when no remote URL exists for a repo.
    """


class UnknownRevision(GitException):
    """
    Thrown when specified revision cannot be found.
    """


class AmbiguousRevision(GitException):
    """
    Thrown when specified revision is ambiguous.
    """

    def __init__(self, message: str, git_command: str, candidates: List[Candidate]) -> None:
        super().__init__(message, git_command)
        self.candidates = candidates


class PipError(DownloaderException):
    """
    Thrown when pip returns a non-zero return code.
    """
