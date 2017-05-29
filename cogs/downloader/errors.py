class DownloaderException(Exception):
    """
    Base class for Downloader exceptions.
    """
    pass


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


class CloningError(DownloaderException):
    """
    Thrown when git clone returns a non zero exit code.
    """
    pass
