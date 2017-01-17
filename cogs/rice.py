import discord

from discord.ext import commands


class riceBot:                                                              #change the classname
    def __init__(self, bot):
        self.bot = bot

    @commands.command(no_pm=True, pass_context=True)
    async def rice(self, ctx):                                              #change the command that starts the function
        """
        Shows bot info about riceBot"""
        channel = ctx.message.channel
        msg = '```asciidoc\n'
        msg += '\n\nWhat is riceBot? :: '                                   #change the name of riceBot to name of your bot
        msg += '\nA depressed Discord bot that has a lot of handy features.'
        msg += 'The bot is currently on '
        msg += str(len(self.bot.servers))
        msg += ' Servers and connected to '
        msg += str(len(set(self.bot.get_all_members())))
        msg += ' users.\nHere is a list of basic commands:'
        msg += '\n```'
        msg += '```md\n'
        msg += '< Contact owner = use rice.contact [message]       >\n'
        msg += '< Get help      = use rice.help or rice.help [command] >\n'
        msg += '\n```'
        await self.bot.say(msg)

        link = '```markdown\n'
        link += 'To add the bot to your own server, '
        link += 'open this [link](https://discordsites.com/ricebot/)'       #add a link - this should be the bot invite link
        link += '\n```'
        await self.bot.say(link)



    async def on_server_join(self, server):
        msg = "```asciidoc\n"
        msg += "Announcement :: Information\n"
        msg += "= -=-=-=-=-=-=-=-=-=-=-=- =\n"
        msg += "Thank you for inviting riceBot!\n"
        msg += "For basic information on the bot, a list of commands, or to contact the owner, use: \n"
        msg += "= rice.rice =\n"
        msg += "= rice.help =\n"
        msg += "= rice.contact =\n"
        msg += "To add the bot to your own server, open this:: https://discordsites.com/ricebot/\n"
        msg += "= -=-=-=-=-=-=-=-=-=-=-=- =\n"
        msg += "riceBot ~ managed by FwiedWice"
        msg += "\n```"
        try:
            await self.bot.send_message(server, msg)
        except:
            pass


def setup(bot):
    n = riceBot(bot)
    bot.add_listener(n.on_server_join)
    bot.add_cog(n)                                               #change the name to what you changed the classname to in line 7
