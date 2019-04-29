class FakeContextAnnouncer:
    """Used for providing a fake context when RPC announcing through Admin, for the Announcer to access the bot"""
    def __init__(self, bot):
        self.bot = bot