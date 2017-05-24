class StreamsError(Exception):
    pass


class StreamNotFound(StreamsError):
    pass


class APIError(StreamsError):
    pass


class InvalidCredentials(StreamsError):
    pass


class OfflineStream(StreamsError):
    pass
