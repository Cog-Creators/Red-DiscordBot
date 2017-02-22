class NoMassMentions:
    """Silences outcoming mass mentions"""

    def __init__(self, bot):
        self.bot = bot
        self.bot.add_message_modifier(self.cleanse_msg)

    def cleanse_msg(self, m):
        return m.replace("@everyone", "@\u200beveryone")\
                .replace("@here", "@\u200bhere")

    def __unload(self):
        self.bot.remove_message_modifier(self.cleanse_msg)


def setup(bot):
    bot.add_cog(NoMassMentions(bot))
