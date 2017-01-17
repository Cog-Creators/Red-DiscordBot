# Discord
import discord
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from .utils import checks
# Essentials
import aiohttp
from fnmatch import fnmatch
import os
from datetime import datetime
from itertools import chain


class GithubCards:
    """Embed GitHub issues and pull requests with a simple to use system!"""

    __author__ = "Controller Network"
    __version__ = "0.0.1"

    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/githubcards/settings.json')
        self.colour = {
            'open': 0x6cc644,
            'closed': 0xbd2c00,
            'merged': 0x6e5494
        }

    @commands.group(pass_context=True, no_pm=True, aliases=['ghc'])
    @checks.admin_or_permissions(Administrator=True)
    async def githubcards(self, ctx):
        """Manage GitHub Cards"""
        server = ctx.message.server
        if server.id not in self.settings:
            self.settings[server.id] = {}
            self.save_json()
        if ctx.invoked_subcommand is None:
            await self.bot.send_cmd_help(ctx)

    @githubcards.command(pass_context=True, no_pm=True)
    async def add(self, ctx, prefix, github):
        """Add a new GitHub repo with the given prefix.

        Format for adding a new GitHub repo is \"Username/Repository\""""
        server = ctx.message.server
        prefix = prefix.lower()  # I'm Lazy okay :(
        if prefix in self.settings[server.id]:
            await self.bot.say('This prefix already exists in this server. Please use something else.')
        elif len(github.split('/')) != 2:
            await self.bot.say('Invalid format. Please use Username/Repository')
        else:
            # Confirm the User/Repo exits, We don't want to try and pull from a non existant repo
            async with aiohttp.get('https://api.github.com/repos/{}'.format(github)) as response:
                if response.status == 404:
                    await self.bot.say('The repository cannot be found.\nMake sure its a public repository.')
                else:
                    fields = {
                        'author': True,
                        'status': True,
                        'comments': True,
                        'description': True,
                        'mergestatus': True,
                        'labels': True,
                        'closedby': False,
                        'locked': False,
                        'assigned': False,
                        'createdat': False,
                        'milestone': False,
                        'reviews': True
                    }
                    self.settings[server.id][prefix] = {'gh': github, 'fields': fields}
                    self.save_json()
                    await self.bot.say('All done, you can now use "{}#issue number" to gather information of an issue\nOr use "githubcards edit"'.format(prefix))

    @githubcards.command(pass_context=True, no_pm=True)
    async def edit(self, ctx, prefix, field=None):
        """Edit the fields that show up on the embed.

        To see what fields are currently enabled use "githubcards edit <prefix>"
        The following options are valid:
        author, assigned, closedby, comments, createdat, description, labels, locked, mergestatus, milestone, status, reviews"""
        fieldlist = ['author', 'assigned', 'closedby', 'comments', 'createdat', 'description', 'labels', 'locked', 'mergestatus', 'milestone', 'status', 'reviews']
        if prefix not in self.settings[ctx.message.server.id]:
            await self.bot.say('This GitHub prefix doesn\'t exist.')
        elif field is None:
            templist = []
            for field, fset in self.settings[ctx.message.server.id][prefix]['fields'].items():
                if fset is True:
                    templist.append('{}: Enabled'.format(field.title()))
                else:
                    templist.append('{}: Disabled'.format(field.title()))
            await self.bot.say('```Fields for {}:\n{}```'.format(prefix, '\n'.join(sorted(templist))))
        elif field.lower() in fieldlist:
            if self.settings[ctx.message.server.id][prefix]['fields'][field] is True:
                self.settings[ctx.message.server.id][prefix]['fields'][field] = False
                self.save_json()
                await self.bot.say('"{}" is now disabled.'.format(field.title()))
            else:
                self.settings[ctx.message.server.id][prefix]['fields'][field] = True
                self.save_json()
                await self.bot.say('"{}" is now enabled.'.format(field.title()))
        else:
            await self.bot.say('The field is not valid, please use one of the following \n\n{}'.format(', '.join(fieldlist)))

    @githubcards.command(pass_context=True, no_pm=True)
    async def remove(self, ctx, prefix):
        """Remove a GitHub prefix"""
        prefix = prefix.lower()
        if prefix in self.settings[ctx.message.server.id]:
            del self.settings[ctx.message.server.id][prefix]
            self.save_json()
            await self.bot.say('Done, ~~it was about time.~~ This GitHub Prefix is now deleted.')
        else:
            await self.bot.say('This GitHub prefix doesn\'t exist.')

    async def get_issue(self, message):
        if message.server.id in self.settings and message.author.bot is False:
            for word in message.content.split(' '):
                for prefix in self.settings[message.server.id]:
                    if fnmatch(word.lower(), '{}#*'.format(prefix)):
                        split = word.split('#')
                        if split[1] is None:
                            break
                        await self.post_issue(message, prefix, split[1])

    async def post_issue(self, message, prefix, number):
        api = 'https://api.github.com/repos/{}/issues/{}'.format(self.settings[message.server.id][prefix]['gh'], number)
        fields = self.settings[message.server.id][prefix]['fields']
        async with aiohttp.get(api, headers={'Accept': 'application/vnd.github.black-cat-preview+json'}) as r:
            # Check is the issue exists
            if r.status == 404:
                return False
            result = await r.json()
            # Check if the issue is a PR
            if 'pull_request' in result:
                issue_type = "pr"
                pr_api = 'https://api.github.com/repos/{}/pulls/{}'.format(self.settings[message.server.id][prefix]['gh'], number)
                async with aiohttp.get(pr_api, headers={'Accept': 'application/vnd.github.black-cat-preview+json'}) as r:
                    pr_result = await r.json()
            else:
                issue_type = "issue"
            # Check if the issue is open, closed or merged.
            if result['state'] == 'open':
                colour = self.colour['open']
            elif issue_type == 'pr' and pr_result['merged'] is True:
                colour = self.colour['merged']
            else:
                colour = self.colour['closed']
            # Check for title and description
            if fields['description'] is True:
                description = result['body']
                embed_description = (description[:175] + '...') if len(description) > 175 else description
                embed = discord.Embed(title='{} #{}'.format(result['title'], result['number']), description=embed_description, url=result['html_url'], colour=colour)
            else:
                embed = discord.Embed(title='{} #{}'.format(result['title'], result['number'], url=result['html_url'], colour=colour))
            if fields['author'] is True:
                embed.set_author(name=result['user']['login'], icon_url=result['user']['avatar_url'], url=result['user']['html_url'])
            # Check for assigned users
            if fields['assigned'] is True and len(result['assignees']) != 0:
                desc = ''
                for assigned in result['assignees']:
                    desc = desc + ('[{}]({})\n'.format(assigned['login'], assigned['html_url']))
                embed.add_field(name='Assigned', value=desc)
            # Check for Created at, Closed at and Closed By
            if fields['createdat'] is True or fields['closedby'] is True:
                desc = ''
                if fields['closedby'] is True and result['state'] == 'closed':
                    closed_user_avatar = result['closed_by']['avatar_url']
                    closed_at = datetime.strptime(result['closed_at'], '%Y-%m-%dT%H:%M:%SZ')
                    closed_at = closed_at.strftime('%-d %b %Y, %-H:%M')
                    desc = desc + 'Closed by {} on {}'.format(result['closed_by']['login'], closed_at)
                if fields['createdat'] is True:
                    created_at = datetime.strptime(result['created_at'], '%Y-%m-%dT%H:%M:%SZ')
                    created_at = created_at.strftime('%-d %b %Y, %-H:%M')
                    if result['state'] == 'closed' and fields['closedby'] is True:
                        desc = desc + ' | Created on {}'.format(created_at)
                    else:
                        desc = desc + 'Created on {}'.format(created_at)
                if result['state'] == 'closed' and fields['closedby'] is True:
                    embed.set_footer(icon_url=closed_user_avatar, text=desc)
                else:
                    embed.set_footer(text=desc)
            # Check for Labels
            if fields['labels'] is True and len(result['labels']) != 0:
                label_list = []
                for label in result['labels']:
                    label_list.append('{}'.format(label['name']))
                embed.add_field(name='Labels [{}]'.format(len(result['labels'])), value=', '.join(label_list))
            # Check for locked Issues
            if fields['locked'] is True:
                if result['locked'] is True:
                    embed.add_field(name='Locked', value='Yes')
                else:
                    embed.add_field(name='Locked', value='No')
            # Check for Merge Status
            if fields['mergestatus'] is True and issue_type == 'pr':
                if pr_result['merged'] is True:
                    merge_status = 'Merged'
                elif pr_result['mergeable_state'] == 'dirty':
                    merge_status = 'Conflicting'
                else:
                    merge_status = 'Not Merged'
                embed.add_field(name='Merge Status', value=merge_status)
            # Milestones: TODO lololololol
            # Check for Reviews
            if fields['reviews'] is True and issue_type == 'pr':
                # Need to make another connection *ugh*. Goodbye quick loading times.
                review_api = 'https://api.github.com/repos/{}/pulls/{}/reviews'.format(self.settings[message.server.id][prefix]['gh'], number)
                async with aiohttp.get(review_api, headers={'Accept': 'application/vnd.github.black-cat-preview+json'}) as r:
                    review_result = await r.json()
                    review_list = []
                    for review in review_result:
                        if review['state'] == 'APPROVED':
                            review_list.append([review['user']['login'], 'Approved'])
                        elif review['state'] == 'CHANGES_REQUESTED':
                            review_list.append([review['user']['login'], 'Requested Changes'])
                    if len(review_list) > 0:
                        desc = ''
                        for user in review_list:
                            desc = desc + '{}: {}'.format(*user)
                        embed.add_field(name='Reviews', value=desc)
            await self.bot.send_message(message.channel, embed=embed)

    def save_json(self):
        dataIO.save_json("data/githubcards/settings.json", self.settings)


def check_folder():
    f = 'data/githubcards'
    if not os.path.exists(f):
        os.makedirs(f)


def check_file():
    f = 'data/githubcards/settings.json'
    if dataIO.is_valid_json(f) is False:
        dataIO.save_json(f, {})


def setup(bot):
    check_folder()
    check_file()
    n = GithubCards(bot)
    bot.add_listener(n.get_issue, 'on_message')
    bot.add_cog(n)
