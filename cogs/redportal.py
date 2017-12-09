from cogs.utils.checks import is_owner_check
from urllib.parse import quote
import discord
from discord.ext import commands
import aiohttp


numbs = {
    "next": "➡",
    "back": "⬅",
    "install": "✅",
    "exit": "❌"
}


class Redportal:
    """Interact with cogs.red through Kermit"""

    def __init__(self, bot):
        self.bot = bot

    @commands.group(pass_context=True, aliases=['redp'])
    async def redportal(self, ctx):
        """Interact with cogs.red through Kermit"""

        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    async def _search_redportal(self, ctx, url):
        # future response dict
        data = None

        try:
            async with aiohttp.get(url, headers={"User-Agent": "Sono-Bot"}) as response:
                data = await response.json()

        except:
            return None

        if data is not None and not data['error'] and len(data['results']['list']) > 0:

            # a list of embeds
            embeds = []

            for cog in data['results']['list']:
                embed = discord.Embed(title=cog['name'],
                                      url='https://cogs.red{}'.format(cog['links']['self']),
                                      description=((cog['description'] and len(cog['description']) > 175 and '{}...'.format(cog['description'][:175])) or cog['description']) or cog['short'],
                                      color=0x2ecc71)
                embed.add_field(name='Type', value=cog['repo']['type'], inline=True)
                embed.add_field(name='Author', value=cog['author']['name'], inline=True)
                embed.add_field(name='Repo', value=cog['repo']['name'], inline=True)
                embed.add_field(name='Command to add repo',
                                value='{}cog repo add {} {}'.format(ctx.prefix, cog['repo']['name'], cog['links']['github']['repo']),
                                inline=False)
                embed.add_field(name='Command to add cog',
                                value='{}cog install {} {}'.format(ctx.prefix, cog['repo']['name'], cog['name']),
                                inline=False)
                embed.set_footer(text='{}{}'.format('{} ⭐ - '.format(cog['votes']),
                                                    (len(cog['tags'] or []) > 0 and '🔖 {}'.format(', '.join(cog['tags']))) or 'No tags set 😢'
                                                    ))
                embeds.append(embed)

            return embeds, data

        else:
            return None

    @redportal.command(pass_context=True)
    async def search(self, ctx, *, term: str):
        """Searches for a cog"""

        try:
            # base url for the cogs.red search API
            base_url = 'https://cogs.red/api/v1/search/cogs'

             # final request url
            url = '{}/{}'.format(base_url, quote(term))

            embeds, data = await self._search_redportal(ctx, url)

            if embeds is not None:
                await self.cogs_menu(ctx, embeds, message=None, page=0, timeout=30, edata=data)
            else:
                await self.bot.say('No cogs were found or there was an error in the process')

        except TypeError:
            await self.bot.say('No cogs were found or there was an error in the process')

    async def cogs_menu(self, ctx, cog_list: list,
                        message: discord.Message=None,
                        page=0, timeout: int=30, edata=None):
        """menu control logic for this taken from
           https://github.com/Lunar-Dust/Dusty-Cogs/blob/master/menu/menu.py"""
        cog = cog_list[page]

        is_owner_or_co = is_owner_check(ctx)
        if is_owner_or_co:
            expected = ["➡", "✅", "⬅", "❌"]
        else:
            expected = ["➡", "⬅", "❌"]

        if not message:
            message =\
                await self.bot.send_message(ctx.message.channel, embed=cog)
            await self.bot.add_reaction(message, "⬅")
            await self.bot.add_reaction(message, "❌")

            if is_owner_or_co:
                await self.bot.add_reaction(message, "✅")

            await self.bot.add_reaction(message, "➡")
        else:
            message = await self.bot.edit_message(message, embed=cog)
        react = await self.bot.wait_for_reaction(
            message=message, user=ctx.message.author, timeout=timeout,
            emoji=expected
        )
        if react is None:
            try:
                try:
                    await self.bot.clear_reactions(message)
                except:
                    await self.bot.remove_reaction(message, "⬅", self.bot.user)
                    await self.bot.remove_reaction(message, "❌", self.bot.user)
                    if is_owner_or_co:
                        await self.bot.remove_reaction(message, "✅", self.bot.user)
                    await self.bot.remove_reaction(message, "➡", self.bot.user)
            except:
                pass
            return None
        reacts = {v: k for k, v in numbs.items()}
        react = reacts[react.reaction.emoji]
        if react == "next":
            page += 1
            next_page = page % len(cog_list)
            try:
                await self.bot.remove_reaction(message, "➡", ctx.message.author)
            except:
                pass
            return await self.cogs_menu(ctx, cog_list, message=message,
                                        page=next_page, timeout=timeout, edata=edata)
        elif react == "back":
            page -= 1
            next_page = page % len(cog_list)
            try:
                await self.bot.remove_reaction(message, "⬅", ctx.message.author)
            except:
                pass
            return await self.cogs_menu(ctx, cog_list, message=message,
                                        page=next_page, timeout=timeout, edata=edata)
        elif react == "install":
            if not is_owner_or_co:
                await self.bot.say("This function is only available to the bot owner.")
                return await self.cogs_menu(ctx, cog_list, message=message,
                                            page=page, timeout=timeout, edata=edata)
            else:
                INSTALLER = self.bot.get_cog('Downloader')
                if not INSTALLER:
                    await self.bot.say("The downloader cog must be loaded to use this feature.")
                    return await self.cogs_menu(ctx, cog_list, message=message,
                                                page=page, timeout=timeout, edata=edata)

                repo1, repo2 = edata['results']['list'][page]['repo']['name'], edata['results']['list'][page]['links']['github']['repo']
                cog1, cog2 = edata['results']['list'][page]['repo']['name'], edata['results']['list'][page]['name']

                await ctx.invoke(INSTALLER._repo_add, repo1, repo2)
                await ctx.invoke(INSTALLER._install, cog1, cog2)

                return await self.bot.delete_message(message)
        else:
            try:
                return await self.bot.delete_message(message)
            except:
                pass


def setup(bot):
    bot.add_cog(Redportal(bot))
