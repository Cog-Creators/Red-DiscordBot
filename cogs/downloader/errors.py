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
