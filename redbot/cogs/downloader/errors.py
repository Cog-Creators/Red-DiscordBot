__all__ = [
    "DownloaderException",
    "GitException",
    "InvalidRepoName",
    "ExistingGitRepo",
    "MissingGitRepo",
    "CloningError",
    "CurrentHashError",
    "HardResetError",
    "UpdateError",
    "GitDiffError",
    "NoRemoteURL",
    "PipError",
]


class DownloaderException(Exception):
    """
    Base class for Downloader exceptions.
    """

    pass


class GitException(DownloaderException):
    """
    Generic class for git exceptions.
    """


class InvalidRepoName(DownloaderException):
    """
    Throw when a repo name is invalid. Check
    the message for a more detailed reason.
    """

    pass


class ExistingGitRepo(DownloaderException):
    """
    Thrown when trying to clone into a folder where a
    git repo already exists.
    """

    pass


class MissingGitRepo(DownloaderException):
    """
    Thrown when a git repo is expected to exist but
    does not.
    """

    pass


class CloningError(GitException):
    """
    Thrown when git clone returns a non zero exit code.
    """

    pass


class CurrentHashError(GitException):
    """
    Thrown when git returns a non zero exit code attempting
    to determine the current commit hash.
    """

    pass


class HardResetError(GitException):
    """
    Thrown when there is an issue trying to execute a hard reset
    (usually prior to a repo update).
    """

    pass


class UpdateError(GitException):
    """
    Thrown when git pull returns a non zero error code.
    """

    pass


class GitDiffError(GitException):
    """
    Thrown when a git diff fails.
    """

    pass


class NoRemoteURL(GitException):
    """
    Thrown when no remote URL exists for a repo.
    """

    pass


class PipError(DownloaderException):
    """
    Thrown when pip returns a non-zero return code.
    """

    pass
