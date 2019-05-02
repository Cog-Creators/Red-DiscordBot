class FakeMessage:
    """Used for providing a fake message to a context, for creating aliases"""

    def __init__(self, botuser, guild):
        self.author = botuser
        self._state = None
        self.guild = guild
