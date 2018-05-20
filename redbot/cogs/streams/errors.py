class StreamsError(Exception):
    pass


class StreamNotFound(StreamsError):
    pass


class CommunityNotFound(StreamsError):
    pass


class APIError(StreamsError):
    pass


class InvalidTwitchCredentials(StreamsError):
    pass


class InvalidYoutubeCredentials(StreamsError):
    pass


class OfflineStream(StreamsError):
    pass


class OfflineCommunity(StreamsError):
    pass
