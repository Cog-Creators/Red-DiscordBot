# -*- coding: utf-8 -*-
class StreamsError(Exception):
    pass


class StreamNotFound(StreamsError):
    pass


class APIError(StreamsError):
    pass


class InvalidTwitchCredentials(StreamsError):
    pass


class InvalidYoutubeCredentials(StreamsError):
    pass


class OfflineStream(StreamsError):
    pass
