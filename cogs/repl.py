from discord.ext import commands
import red
from cogs.utils import checks
from cogs.utils.dataIO import dataIO
from cogs.utils.chat_formatting import pagify
import asyncio
import traceback
import discord
import inspect
from contextlib import redirect_stdout
from __main__ import send_cmd_help
import io
import os
import re
import subprocess
from collections import OrderedDict
from collections import MutableSequence


# TODO: rtfs
# X  * functionify
# X  * commandify
#   * option to open file in text editor
#   * Cogs
#   * path/file.py
#   * cog info / author
#       * look in downloads if not found
#           * mention that it's not installed
#   * shorter error message
# X TODO: set repl character `
# X TODO: set pager characters
# TODO: set page length per repl prefix (mobile)
# X TODO: replace repl's dir with dir(bot) - 'react' | dir(bot)['react']
# X   or make that ddir() instead.. or Dir()
# X TODO: constrain command evals
# X TODO: format command errors
# TODO: merge with REPL
# TODO: still listen for code blocks if ` is included in the prefix list
# TODO: pager length on \n?
# TODO: REPL Sessions 😱
#   * load/save (reeval) all history starting from [p]repl
#   * save input/output history viewable later (log file + pager reader?)
# TODO: [p]dir+, [p]dir- ([p]dir +/ [p]dir -), [p]pyhelp ^ (or default) (or both so can ^.attr)
#   * save previous [p]dirs and add +/- to it (search/exclude)
#   * [p]pyhelp with "^"" and/or blank gets help for dir'd thing
#       (or singled attr or ^.search if search returns single attr)
#   * [p]dir ^.search dirs the next layer down if search returns a single attr
#
#
# TODO:
"""
def __getattr__(self, attr):
    try:
        return self.__dict__[attr]
    except:
        if attr in self._exclusions:
            return NotImplemented
        return getattr(self.__superclass, attr)
"""


class ReactionRemoveEvent(asyncio.Event):
    def __init__(self, emojis, author):
        super().__init__()
        self.emojis = emojis
        self.author = author
        self.reaction = None

    def set(self, reaction):
        self.reaction = reaction
        return super().set()


def irdir(*args, re_exclude=None, re_search=None):
    """Dir([object[,re_exclude[,re_search]]]) --> Dir[list of attributes]
    slightly more useful dir() with search/exclusion

    returns a Dir object.

    Like built-in function dir,
    If called without an argument, return the names in the current scope.
    Else, return an alphabetized list of names comprising (some of) the attributes
    of the given object, and of attributes reachable from it.

    If re_exclude or re_search arguments are given,
    they are used as exclusion and search regexes on the object's list of attributes/
    If left blank, private and protected attributes are excluded by default

    Dir() objects can have their search/exclusion regexes added to via the operator pairs:
    Search, Exclusion
    -----------------
         +, -
         @, //
        [], del (also provides indexed get/deletion)
    search, exclude (methods)

    * done as a function for more legible help()
    ** At the moment there are many unimplemented list-like methods. Most of them don't work.
       I will remove them later. If you need it to act like a list instead of a Dir, just list(it)
    """
    return Dir(*args, re_exclude=re_exclude, re_search=re_search)


class Dir(MutableSequence):
    """Dir([object[,re_exclude[,re_search]]]) --> Dir[list of attributes]
    slightly more useful dir() with search/exclusion

    Like built-in function dir,
    If called without an argument, return the names in the current scope.
    Else, return an alphabetized list of names comprising (some of) the attributes
    of the given object, and of attributes reachable from it.

    If re_exclude or re_search arguments can be strings or lists of patterns.
    If given, they are used as exclusion and search regexes on the object's list of attributes.
    If left blank, private and protected attributes are excluded by default.

    Dir() objects can have their search/exclusion regexes added to via the operator pairs:
    Search, Exclusion
    -----------------
         +, -
         @, //
        [], del (also provides indexed get/deletion)
    search, exclude (methods)

    ** At the moment there are many unimplemented list-like methods. Most of them don't work.
       I will remove them later. If you need it to act like a list instead of a Dir, just list(it)
    """

    def __init__(self, *args, re_exclude=None, re_search=None):
        # thing, re_search=[], re_exclude: str="^_"
        args = list(args)
        nargs = sum([True] * len(args) +
                    [re_exclude is not None] +
                    [re_search is not None])
        if nargs > 3:
            raise TypeError("dir expected at most 3 arguments, "
                            "got {}".format(nargs))
        kwargs = {}
        keys = ["object", "re_exclude", "re_search"]
        for k in keys:
            if args:
                kwargs[k] = args.pop(0)
        if re_exclude is not None:
            kwargs["re_exclude"] = re_exclude
        if re_search is not None:
            kwargs["re_search"] = re_search

        re_exclude = kwargs.get("re_exclude", ['^_'])
        re_search = kwargs.get("re_search", [])

        try:
            self._object = kwargs["object"]
            self.list = dir(self._object)
        except:
            # dir() and locals() show this namespace.
            # globals() shows this's global namespace
            # don't know how to make this act like it's in the repl
            raise TypeError('please use dir() to see locals')
            self.list = ["please use dir() to see locals"]
        if isinstance(re_search, str):
            re_search = [re_search]
        if isinstance(re_exclude, str):
            re_exclude = [re_exclude]
        self._re_search = list(re_search)  # in case a tuple is given
        self._re_exclude = list(re_exclude)
        self._search()
        self._exclude()

    def __str__(self):
        return "Dir{}".format(str(self.list))

    def __repr__(self):
        try:
            return ("<Dir object({}, re_exclude={}, re_search={})>"
                    .format(repr(self._object),
                            repr(self._re_exclude),
                            repr(self._re_search)))
        except:
            return ("<Dir object(re_exclude={}, re_search={})>"
                    .format(repr(self._re_exclude),
                            repr(self._re_search)))

    def _search(self, add: str=None):
        if add:
            self._re_search.append(add)
        for s in self._re_search:
            self.list = [i for i in self.list if re.search(s, i)]

    def _exclude(self, add: str=None):
        if add:
            self._re_exclude.append(add)
        re_exclude = '|'.join(self._re_exclude)
        self.list = [i for i in self.list if not re.search(re_exclude, i)]

    def __len__(self): return len(self.list)

    def __getitem__(self, i):
        """returns the i'th item.
        If i is a str, returns a new Dir instance with a more constrained search"""
        return self.search(i) if isinstance(i, str) else self.list[i]

    def __matmul__(self, other: str):
        """returns a new Dir instance with a more constrained search"""
        return self.search(other) if isinstance(other, str) else NotImplemented

    def __add__(self, other: str):
        """returns a new Dir instance with a more constrained search"""
        return self.search(other) if isinstance(other, str) else NotImplemented

    def __delitem__(self, i):
        """removes the i'th item.
        If i is a str, adds i to the list of excluded regex"""
        if isinstance(i, str):
            self._exclude(i)
        else:
            del self.list[i]

    def __floordiv__(self, other: str):
        """returns a new Dir instance with an added exclusion"""
        return self.exclude(other) if isinstance(other, str) else NotImplemented

    def __sub__(self, other: str):
        """returns a new Dir instance with an added exclusion"""
        return self.exclude(other) if isinstance(other, str) else NotImplemented

    def __setitem__(self, i, v):
        return NotImplemented

    def insert(self, i, x):
        return NotImplemented

    def search(self, re_search: str):
        """returns a new Dir instance with a more constrained search"""
        if hasattr(self, '_object'):
            return Dir(self._object, re_exclude=self._re_exclude,
                       re_search=self._re_search + [re_search])
        return Dir(re_exclude=self._re_exclude,
                   re_search=self._re_search + [re_search])

    def exclude(self, re_exclude: str):
        """returns a new Dir instance with an added exclusion"""
        if hasattr(self, '_object'):
            return Dir(self._object, re_exclude=self._re_exclude + [re_exclude],
                       re_search=self._re_search)
        return Dir(re_exclude=self._re_exclude + [re_exclude],
                   re_search=self._re_search)


class Source:
    def __init__(self, cmd):
        self.filename = inspect.getsourcefile(cmd)
        source = inspect.getsourcelines(cmd)
        self.line_number = source[1]
        self.source = ''.join(source[0])


class REPL:
    def __init__(self, bot):
        self.bot = bot
        self.settings = dataIO.load_json('data/repl/settings.json')
        self.output_file = "data/repl/temp_output.txt"
        self.sessions = set()
        self.reaction_remove_events = {}

    def repl_format_source(self, thing):
        """returns get_source formatted to be used in repl

        rtfs originated as this alias:
        debug (lambda cmd, bot=bot: (lambda f, out: out[0] if len(out) == 1 else (f(f,out[1:5] + (['{} more pages remaining..\njust tell them to read the actual source file man.'.format(len(out)-5)] if len(out) > 5 else [])) or out[0]))((lambda self, more: None if not more else bot.loop.create_task(bot.say('``'+'`py\n'+more.pop(0)+'``'+'`')).add_done_callback(self(self, more))), list(pagify((lambda ic, fc, pg: (lambda fcs: ic.getsourcefile(fc).split('/')[-1]+'\nline: {}'.format(fcs[1])+'``'+'`'+'\n'+'``'+'`py\n'+''.join(fcs[0]))(ic.getsourcelines(fc)))(__import__('inspect'), (cmd if not isinstance(cmd, str) else (lambda f, ms: f(f, __import__(ms.pop(0)), ms))((lambda f, prev, ms: getattr(prev, 'callback') if hasattr(prev, 'callback') else prev if not ms else f(f, getattr(prev, ms.pop(0)), ms)), cmd.split('.')) if '.' in cmd else (lambda end, cmds: end(end, cmds, bot.commands[cmds.pop(0)]).callback)((lambda end, names, cmd: cmd if not names else end(end, names, cmd.commands[names.pop(0)])), cmd.split()) ), __import__('cogs').utils.chat_formatting.pagify), delims=['\n', ' '], escape=False, shorten_by=12)) ))
        """
        source = self.get_source(thing)
        msg =  source.filename.split('/')[-1] + '\n'
        msg += 'line: {}'.format(source.line_number)
        msg += '``'+'`\n`'+'``py\n'  # codeblock break
        msg += source.source
        return msg

    def get_source(self, thing):
        """returns a source object of a thing

        thing may be a non-builtin module, class, method, function, traceback, frame, or code object,
        or a space separated discord.ext.commands call,
        or a period deliminated file/module path as used when importing
        """
        if isinstance(thing, str):
            if '.' in thing:  # import
                modules = thing.split('.')
                def get_last_attr(prev, attrs):
                    try:
                        return prev.callback
                    except AttributeError:
                        if not attrs:
                            return prev
                        return get_last_attr(getattr(prev, attrs.pop(0)),
                                                     attrs)
                thing = get_last_attr(__import__(modules.pop(0)), modules)
            else:  # space delimited command call
                names = thing.split()
                thing = self.bot.commands[names.pop(0)]
                for name in names:
                    thing = thing.commands[name]
                thing = thing.callback
        return Source(thing)

    def cleanup_code(self, content):
        """Automatically removes code blocks from the code."""
        # remove ```py\n```
        if content.startswith('```') and content.endswith('```'):
            return '\n'.join(content.split('\n')[1:-1])

        # remove `foo`
        for p in self.settings["REPL_PREFIX"]:
            if content.startswith(p):
                if p == '`':
                    return content.strip('` \n')
                content = content[len(p):]
                return content.strip(' \n')

    def get_syntax_error(self, e):
        return '```py\n{0.text}{1:>{0.offset}}\n{2}: {0}```'.format(e, '^', type(e).__name__)

    async def print_results(self, ctx, results):
        msg = ctx.message
        nbs = '​'
        discord_fmt = nbs + '```py\n{}\n```'
        is_interactive = self.settings["OUTPUT_REDIRECT"] == "pages"
        res_len = len(discord_fmt.format(results))
        if is_interactive and res_len > self.settings["PAGES_LENGTH"]:
            page = self.interactive_results(ctx, results,
                                            single_msg=not self.settings["MULTI_MSG_PAGING"])
            self.bot.loop.create_task(page)
        elif res_len > 2000:
            if self.settings["OUTPUT_REDIRECT"] == "pm":
                await self.bot.send_message(msg.channel, 'Content too big. Check your PMs')
                enough_paper = self.settings["PM_PAGES"]
                for page in pagify(results, ['\n', ' '], shorten_by=12):
                    await self.bot.send_message(msg.author, discord_fmt.format(page))
                    enough_paper -= 1
                    if not enough_paper:
                        await self.bot.send_message(msg.author,
                                                    "**Too many pages! Think of the trees!**")
                        return
            elif self.settings["OUTPUT_REDIRECT"] == "console":
                await self.bot.send_message(msg.channel, 'Content too big. Check your console')
                print(results)
            else:
                await self.bot.send_message(msg.channel, 'Content too big. Writing to file')
                with open(self.output_file, 'w') as f:
                    f.write(results)
                open_cmd = self.settings["OPEN_CMD"]
                if open_cmd:
                    subprocess.Popen([open_cmd, self.output_file])
        else:

            await self.bot.send_message(msg.channel, discord_fmt.format(results))

    async def interactive_results(self, ctx, results, single_msg=True):
        author = ctx.message.author
        channel = ctx.message.channel

        if single_msg:
            choices = OrderedDict((('◀', 'prev'),
                                   ('❌', 'close'),
                                   ('▶', 'next')))
        else:
            choices = OrderedDict((('❌', 'close'),
                                   ('🔽', 'next')))

        nbs = '​'
        discord_fmt = nbs + '```py\n{}\n```'
        prompt = ("  Output too long. Navigate pages with ({})"
                  .format('/'.join(choices.values())))

        pages = [p for p in pagify(results, ['\n', ' '],
                                   page_length=self.settings["PAGES_LENGTH"])]
        # results is not a generator, so no reason to keep this as one
        pages = [discord_fmt.format(p) + 'pg. {}/{}'
                 .format(c + 1, len(pages))
                 for c, p in enumerate(pages)]
        pages[0] += prompt

        choice = 'next'
        page_num = 0
        dirs = {'next': 1, 'prev': -1}
        msgs = []
        while choice:
            msg = await self.display_page(pages[page_num], channel, choices,
                                          msgs, single_msg)
            choice = await self.wait_for_interaction(msg, author, choices)
            if choice == 'close':
                try:
                    await self.bot.delete_messages(msgs)
                except:  # selfbots
                    for m in msgs:
                        await self.bot.delete_message(m)
                break
            if choice in dirs:
                page_num = (page_num + dirs[choice]) % len(pages)
        if choice is None:
            await self.remove_reactions(msgs.pop())

    async def remove_reactions(self, msg):
        channel = msg.channel
        botm = msg.server.me
        if botm.permissions_in(channel).manage_messages:
            await self.bot.clear_reactions(msg)
        else:
            await asyncio.gather(*(self.bot.remove_reaction(msg, r.emoji, botm)
                                   for r in msg.reactions if r.me),
                                 return_exceptions=True)

    async def display_page(self, page, channel, emojis, msgs, overwrite_prev):
        if msgs and overwrite_prev:
            msg = msgs.pop()
            embed = msg.embeds[0] if len(msg.embeds) else None
            msg = await self.bot.edit_message(msg, new_content=page, embed=embed)
        else:
            send_msg = self.bot.send_message(channel, page)
            if msgs:
                # refresh msg
                prv_msg = await self.bot.get_message(channel, msgs[len(msgs) - 1].id)
                tasks = (send_msg, self.remove_reactions(prv_msg))
                results = await asyncio.gather(*tasks, return_exceptions=True)
                msg = results[0]
            else:
                msg = await send_msg
            try:
                async def add_emojis(m, es):
                    try:
                        for e in es:  # we want these to be in order
                            await self.bot.add_reaction(m, e)
                    except discord.errors.NotFound:
                        # was deleted before we could react
                        pass
                # but we don't want to wait
                self.bot.loop.create_task(add_emojis(msg, emojis))
            except:
                pass
        msgs.append(msg)
        return msg

    async def wait_for_interaction(self, msg, author, choices: OrderedDict,
                                   timeout=120, delete_msg=True,
                                   match_first_char=True):
        """waits for a message or reaction add/remove
        If the response is a msg,
            schedules msg deletion it if delete_msg
            also match 1 character msgs to the choice if match_first_char
        """

        emojis = tuple(choices.keys())
        words = tuple(choices.values())
        first_letters = {w[0]: w for w in words}

        def mcheck(msg):
            lm = msg.content.lower()
            return (lm in words or
                    (match_first_char and lm in first_letters))

        tasks = (self.bot.wait_for_message(author=author, timeout=timeout,
                                           channel=msg.channel, check=mcheck),
                 self.bot.wait_for_reaction(user=author, timeout=timeout,
                                            message=msg, emoji=emojis),
                 self.wait_for_reaction_remove(user=author, timeout=timeout,
                                               message=msg, emoji=emojis))

        def msgconv(msg):
            res = msg.content.lower()
            if res not in words:
                res = first_letters[res]

            async def try_del():
                try:
                    await self.bot.delete_message(msg)
                except:
                    pass
            self.bot.loop.create_task(try_del())
            return res

        def mojichoice(r):
            return choices[r.reaction.emoji]

        converters = (msgconv, mojichoice, mojichoice)
        return await wait_for_first_response(tasks, converters)

    async def wait_for_reaction_remove(self, emoji=None, *, user=None,
                                       timeout=None, message=None, check=None):
        """Waits for a reaction to be removed by a user from a message within a time period.
        Made to act like other discord.py wait_for_* functions but is not fully implemented.

        Because of that, wait_for_reaction_remove(self, emoji: list, user, message, timeout=None)
        is a better representation of this function's def

        returns the actual event or None if timeout
        """
        if not (emoji and user and message) or check or isinstance(emoji, str):
            raise NotImplementedError("wait_for_reaction_remove(self, emoji, "
                                      "user, message, timeout=None) is a better "
                                      "representation of this function definition")
        remove_event = ReactionRemoveEvent(emoji, user)
        self.reaction_remove_events[message.id] = remove_event
        done, pending = await asyncio.wait([remove_event.wait()],
                                           timeout=timeout)
        res = self.reaction_remove_events.pop(message.id)
        try:
            return done.pop().result() and res
        except:
            return None

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def dir(self, ctx, thing: str,
                  re_search: str=".*", re_exclude: str="^_"):
        """displays the attributes of a thing

        provide a second argument as a regex pattern to search for within the list
        provide a third exclude pattern to exclude those matches from the list
        defaults to excluding items starting with an underscore "_"

        Note: be careful with double quotes since discord.py parses those as strings"""
        # re_search = re.escape(re_search)
        # re_exclude = re.escape(re_exclude)
        msg = ctx.message

        variables = {
            'ctx': ctx,
            'bot': self.bot,
            'message': msg,
            'server': msg.server,
            'channel': msg.channel,
            'author': msg.author
        }

        def call(thing, variables):
            return repr([a for a in dir(eval(thing, variables))
                         if not re.search(re_exclude, a)
                         and re.search(re_search, a)])

        closure = _close(call, thing, variables)
        await self.print_results(ctx, _call_catch_fmt(closure, 0))

    @commands.command(pass_context=True, aliases=['rtfh'])
    @checks.is_owner()
    async def pyhelp(self, ctx, *, thing: str):
        """displays the help documentation for a python thing"""
        msg = ctx.message

        variables = {
            'ctx': ctx,
            'bot': self.bot,
            'message': msg,
            'server': msg.server,
            'channel': msg.channel,
            'author': msg.author
        }

        def call(thing, variables):
            return help(eval(thing, variables))

        closure = _close(call, thing, variables)
        await self.print_results(ctx, _call_catch_fmt(closure, 0))

    @commands.command(pass_context=True)
    @checks.is_owner()
    async def rtfs(self, ctx, *, thing: str):
        """tries to show the source file of a thing

        thing may be a non-builtin module, class, method, function, traceback, frame, or code object,
        or if surrounded by single or double quotes,
            a space separated discord.ext.commands call,
            or a period deliminated file/module path as used when importing"""
        msg = ctx.message

        variables = {
            'ctx': ctx,
            'bot': self.bot,
            'message': msg,
            'server': msg.server,
            'channel': msg.channel,
            'author': msg.author
        }

        def call(thing, variables):
            return self.repl_format_source(eval(thing, variables))

        closure = _close(call, thing, variables)
        await self.print_results(ctx, _call_catch_fmt(closure, 0))

    @commands.command(pass_context=True, hidden=True)
    @checks.is_owner()
    async def repl(self, ctx):
        msg = ctx.message

        variables = {
            'ctx': ctx,
            'bot': self.bot,
            'message': msg,
            'server': msg.server,
            'channel': msg.channel,
            'author': msg.author,
            'rtfs': self.repl_format_source,
            'Dir': irdir,
            '_': None,
        }

        if msg.channel.id in self.sessions:
            await self.bot.say('Already running a REPL session in this channel. Exit it with `quit`.')
            return

        self.sessions.add(msg.channel.id)
        await self.bot.say('Enter code to execute or evaluate. `exit()` or `quit` to exit.')
        while True:
            def check(m):
                ps = tuple(self.settings["REPL_PREFIX"])
                return m.content.startswith(ps)
            response = await self.bot.wait_for_message(author=msg.author, channel=msg.channel,
                                                       check=check)

            cleaned = self.cleanup_code(response.content)

            if cleaned in ('quit', 'exit', 'exit()'):
                await self.bot.say('Exiting.')
                self.sessions.remove(msg.channel.id)
                return

            executor = exec
            if cleaned.count('\n') == 0:
                # single statement, potentially 'eval'
                try:
                    code = compile(cleaned, '<repl session>', 'eval')
                except SyntaxError:
                    pass
                else:
                    executor = eval

            if executor is exec:
                try:
                    code = compile(cleaned, '<repl session>', 'exec')
                except SyntaxError as e:
                    await self.bot.say(self.get_syntax_error(e))
                    continue

            variables['message'] = response

            fmt = None
            stdout = io.StringIO()

            try:
                with redirect_stdout(stdout):
                    result = executor(code, variables)
                    if inspect.isawaitable(result):
                        result = await result
            except Exception as e:
                value = stdout.getvalue()
                fmt = '{}{}'.format(value, traceback.format_exc())
            else:
                value = stdout.getvalue()
                if result is not None:
                    fmt = '{}{}'.format(value, result)
                    variables['_'] = result
                elif value:
                    fmt = '{}'.format(value)

            try:
                if fmt is not None:
                    await self.print_results(ctx, fmt)
            except discord.Forbidden:
                pass
            except discord.HTTPException as e:
                await self.bot.send_message(msg.channel, 'Unexpected error: `{}`'.format(e))

    @commands.group(pass_context=True)
    @checks.is_owner()
    async def replset(self, ctx):
        """global repl settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @replset.group(pass_context=True, name="print")
    async def replset_print(self, ctx):
        """Sets where repl content goes when response is too large."""
        if ctx.invoked_subcommand is None or \
                isinstance(ctx.invoked_subcommand, commands.Group):
            await send_cmd_help(ctx)

    @replset.command(pass_context=True, name="pagelength")
    async def replset_pagelength(self, ctx, length: int=1500):
        """Sets the page length when using the [p]replset print pages option

        length must be between 300 and 1700.
        length defaults to 1500"""
        if not (300 <= length <= 1700):
            return await send_cmd_help(ctx)
        old_length = self.settings["PAGES_LENGTH"]
        self.settings["PAGES_LENGTH"] = length
        dataIO.save_json("data/repl/settings.json", self.settings)
        await self.bot.say("each page will now break at {} characters "
                           "(was {})".format(length, old_length))

    @replset.command(pass_context=True, name="prefix")
    async def replset_prefix(self, ctx, *prefixes):
        """Sets the prefixes repl looks for.

        Defaults to `
        Note: choosing prefixes that don't include ` will mean that
        repl no longer listens for code blocks"""
        if not prefixes:
            prefixes = ('`',)
        prefixes = sorted(prefixes, reverse=True)
        old_prefixes = self.settings["REPL_PREFIX"]
        self.settings["REPL_PREFIX"] = prefixes
        dataIO.save_json("data/repl/settings.json", self.settings)
        await self.bot.say("repl will now respond to {}. Before the prefixes "
                           "were {}".format(prefixes, old_prefixes))

    @replset_print.command(pass_context=True, name="file")
    async def replset_print_file(self, ctx, choice=None):
        """write results to a file, optionally opening in subl/atom

        Choices: nothing | subl | subl.exe | atom | atom.exe"""
        author = ctx.message.author
        choices = ['subl', 'subl.exe', 'atom', 'atom.exe']
        if choice not in choices + [None, 'nothing']:
            await send_cmd_help(ctx)
            return
        if choice is None:
            msg = ("You chose to print to file. What would you like to open it with?\n"
                   "Choose between:  {}".format(' | '.join(choices + ['nothing'])))
            choice = await self.user_choice(author, msg, choices)
        msg = "repl overflow will now go to file and "
        if choice not in choices:
            msg += "I won't open it after writing to {}".format(self.output_file)
            choice = None
        else:
            msg += ("the output will be opened with: `{} "
                    "{}`".format(choice, self.output_file))
        self.settings['OPEN_CMD'] = choice
        self.settings["OUTPUT_REDIRECT"] = "file"
        dataIO.save_json("data/repl/settings.json", self.settings)
        await self.bot.say(msg)

    @replset_print.command(pass_context=True, name="pages")
    async def replset_print_pages(self, ctx, add_pages: bool=False):
        """navigable pager in the current channel..

        set add_pages to true if you prefer the bot sending a new message for every new page"""
        msg = "repl overflow will now go to pages in the channel and "
        if add_pages:
            msg += "you will be given the option to page via adding new pages"
        else:
            msg += "regular single-message paging will be used"
        self.settings['MULTI_MSG_PAGING'] = add_pages
        self.settings["OUTPUT_REDIRECT"] = "pages"
        dataIO.save_json("data/repl/settings.json", self.settings)
        await self.bot.say(msg)

    @replset_print.command(pass_context=True, name="console")
    async def replset_print_console(self, ctx):
        """print results to console"""
        self.settings["OUTPUT_REDIRECT"] = "console"
        dataIO.save_json("data/repl/settings.json", self.settings)
        await self.bot.say("repl overflow will now go to console")

    @replset_print.command(pass_context=True, name="pm")
    async def replset_print_pm(self, ctx, number_of_pages: int=20):
        """send pages to pm. Defaults to 20"""
        number_of_pages = max(number_of_pages, 1)
        self.settings["OUTPUT_REDIRECT"] = "pm"
        self.settings["PM_PAGES"] = number_of_pages
        dataIO.save_json("data/repl/settings.json", self.settings)
        await self.bot.say("repl overflow will now go to pm with a maximum of "
                           "{} messages".format(number_of_pages))

    async def user_choice(self, author, msg, choices, timeout=20):
        """prompts author with msg. if answer is not in choices, return None,
        otherwise returns response lowered.
        Times out 20 seconds by default"""
        await self.bot.say(msg)
        choices = [c.lower() for c in choices]
        answer = await self.bot.wait_for_message(timeout=timeout,
                                                 author=author)
        answer = answer and answer.content.lower()
        return answer if answer in choices else None

    async def on_reaction_remove(self, reaction, user):
        """Handles watching for reactions for wait_for_reaction_remove"""
        event = self.reaction_remove_events.get(reaction.message.id, None)
        if (event and not event.is_set() and
            user == event.author and
            reaction.emoji in event.emojis):
            event.set(reaction)


def _call_catch_fmt(call, limit=None):
    stdout = io.StringIO()
    try:
        with redirect_stdout(stdout):
            result = call()
    except Exception as e:
            value = stdout.getvalue()
            fmt = '{}{}'.format(value, traceback.format_exc(limit))
    else:
        value = stdout.getvalue()
        fmt = (value or '') + ('' if result is None else result)
    return fmt


def _close(f, *args, **kwargs):
    def call():
        return f(*args, **kwargs)
    return call


async def wait_for_first_response(tasks, converters):
    """given a list of unawaited tasks and non-coro result parsers to be called on the results,
    this function returns the 1st result that is returned and converted

    if it is possible for 2 tasks to complete at the same time,
    only the 1st result deteremined by asyncio.wait will be returned

    returns None if none successfully complete
    returns 1st error raised if any occur (probably)
    """
    primed = [wait_for_result(t, c) for t, c in zip(tasks, converters)]
    done, pending = await asyncio.wait(primed, return_when=asyncio.FIRST_COMPLETED)
    for p in pending:
        p.cancel()

    try:
        return done.pop().result()
    except:
        return None


async def wait_for_result(task, converter):
    """await the task call and return its results parsed through the converter"""
    # why did I do this?
    return converter(await task)


def check_folders():
    folder = "data/repl"
    if not os.path.exists(folder):
        print("Creating {} folder...".format(folder))
        os.makedirs(folder)


def check_files():
    default = {"OUTPUT_REDIRECT": "pages", "OPEN_CMD": None,
               "MULTI_MSG_PAGING": False, "PM_PAGES": 20,
               "PAGES_LENGTH": 1500, "REPL_PREFIX": ['`']}
    settings_path = "data/repl/settings.json"

    if not os.path.isfile(settings_path):
        print("Creating default repl settings.json...")
        dataIO.save_json(settings_path, default)
    else:  # consistency check
        current = dataIO.load_json(settings_path)
        if current.keys() != default.keys():
            for key in default.keys():
                if key not in current.keys():
                    current[key] = default[key]
                    print(
                        "Adding " + str(key) + " field to repl settings.json")
            dataIO.save_json(settings_path, current)


def setup(bot: red.Bot):
    check_folders()
    check_files()
    bot.add_cog(REPL(bot))
