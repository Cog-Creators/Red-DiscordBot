import discord
import os
import re
import random 
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from copy import deepcopy
from .utils import checks
from __main__ import send_cmd_help
from .utils.sync import Route
import urllib
from types import SimpleNamespace

RESOURCES = "data/smashing/"

class Helper:
    """Contains most smash-based static commands"""

    def __init__(self, bot, resources_folder):
        self.bot = bot
        self.melee_chars = dataIO.load_json(RESOURCES+"melee_chars.json")
        self.movelist = dataIO.load_json(RESOURCES+"movelist.json")
        self.privilege = dataIO.load_json(RESOURCES+"character_privilege.json")
        self.char_icons = dataIO.load_json(RESOURCES+"char_icons.json")
        self.emoji = {
            "next": "➡",
            "back": "⬅"
        }

    def _get_move(self, move):
        """Returns a valid move name, from a stored list of aliases."""
        try:
            move = self.movelist[re.sub(r"\s", "", move.lower())]
            #movedata = dataIO.load_json(RESOURCES+"frames/melee/"+move+".json")
            return move
        except:
            raise KeyError("Couldn't find the move {}.".format(str(move)))

    # Is guaranteed to be passed valid character names
    def _get_privilege(self, char):
        try:
            info = self.privilege[char]
        except:
            self.privilege[char] = {}
            self.privilege[char]["facts"] = []
            self.privilege[char]["complaints"] = []
            self._save_privilege()
        return deepcopy(self.privilege[char])

    def _get_character_name(self, character):
        """Returns a valid character name, from a stored list of aliases."""
        try:
            return self.melee_chars[re.sub(r"\s", "", character.lower())]
        except:
            raise KeyError("Couldn't find the character {}.".format(str(character)))

    def _get_character_data(self, character):
        try:
            return dataIO.load_json(RESOURCES+"frames/melee/"+character+".json")
        except:
            raise KeyError("Couldn't find the JSON character data for {}".format(str(character)))

    def _save_privilege(self):
        dataIO.save_json(RESOURCES+"character_privilege.json", self.privilege)
    
    def _save_char(self, char, data):
        dataIO.save_json(RESOURCES+"frames/melee/"+char+".json", data)

    @commands.group(pass_context=True, no_pm=True)
    async def smash(self, ctx):
        """Changes smash module settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    def _form_frame_data_embed(self, data, char, move, state=None):
        """Private method to handle specific logic for forming an embed in the context of certain 'priority' fields"""
        embed = discord.Embed()
        embed.set_author(name="Frame data and animation for: "+char+"'s "+move, icon_url="https://i.imgur.com/"+self.char_icons[char]+".png")
        if state:
            embed.description=state+" version"
        if "URL" in data:
            embed.set_image(url="https://i.imgur.com/"+data["URL"]+".gif")
        if move == "grab":
            priority_fields = [ "Grab total frames", "Grab hits", "Dashgrab total frames", "Dashgrab hits" ]
        else:
            priority_fields = [ "Total frames", "SAF", "Hits" ]
        for field in priority_fields:
            try:
                embed.add_field(name=field, value=data[field], inline=True)
            except:
                pass 
        priority_fields.append("URL")
        for key in data:
            if key not in priority_fields and key != "Notes":
                embed.add_field(name=key, value=data[key], inline=True)

        if "Notes" in data:
            notes='\n'.join(data["Notes"])
            embed.add_field(name="Notes", value='\n'.join(data["Notes"]), inline=False)
        embed.colour=discord.Colour(0xffffff)
        embed.set_footer(text="Plugin by Swann, data by Stratocaster and SDM with thanks to Skytch, Eviox, Savestate.")
        return embed

    async def _show_menu(self, ctx, message, messages):
        if message:
            if type(message) == discord.Embed:
                await self.bot.edit_message(message, embed=messages)
            else:
                await self.bot.edit_message(message, messages)
        else:
            if type(messages) == discord.Embed:
                return await self.bot.send_message(ctx.message.channel, embed=messages)
            else:
                return await self.bot.say(messages)

    async def _menu(self, ctx, messages, **kwargs):
        """Creates and manages a new menu."""
        page = kwargs.get("page", 0)
        timeout = kwargs.get("timeout", 30)
        is_open = kwargs.get("is_open", True)
        emoji = kwargs.get("emoji", self.emoji)
        message = kwargs.get("message", None)
        choices = len(messages)

        if not message:
            message = await self._show_menu(ctx, message, messages[page])
        else:
            message = await self.bot.edit_message(message, embed=messages[page])

        await self.bot.add_reaction(message, str(emoji['back']))
        await self.bot.add_reaction(message, str(emoji['next']))

        r = await self.bot.wait_for_reaction(
                message=message,
                user=ctx.message.author,
                check=None,
                timeout=timeout)
        if r is None:
            await self.bot.clear_reactions(message)
            return [None, message]

        reacts = {v: k for k, v in emoji.items()}
        react = reacts[r.reaction.emoji]

        if react == "next":
            page += 1
        if react == "back":
            page -= 1

        if page < 0:
            page = choices - 1

        if page == choices:
            page = 0

        perms = ctx.message.channel.permissions_for(ctx.message.server.get_member(self.bot.user.id))
        if perms.manage_messages:
            await self.bot.remove_reaction(message, emoji[react], r.user)
        else:
            await self.bot.delete_message(message)
            message = None

        return await self._menu(ctx, messages,
                page=page, timeout=timeout,
                check=None, is_open=is_open,
                emoji=emoji, message=message)

    @smash.command(pass_context=True, no_pm=False)
    async def frames(self, ctx, character : str, move : str):
        """Retrieve the frame data and gfy for a move"""
        # Catch and fix swapped order of character and move
        try:
            char = self._get_character_name( character )
            atk = self._get_move( move )
            atk_data = self._get_character_data( char )[atk]
        except KeyError as e:
            try:
                char = self._get_character_name( move )
                atk = self._get_move( character )
                move = character
                atk_data = self._get_character_data(char)[atk]
            except KeyError as e:
                print(e)
                return
            print(e)
        # Check for multi-faceted moves
        if "Total frames" not in atk_data and "Hits" not in atk_data:
            embeds = []
            for state in atk_data:
                embeds.append(self._form_frame_data_embed(atk_data[state], char, move, state))
            # Call method to show multi-faceted move as a collection of Embeds
            #  via a reaction-driven menu interface.
            await self._menu(ctx, embeds)
        else:
            data=self._form_frame_data_embed(atk_data, char, move)
            await self.bot.say(embed=data)

    @smash.command(pass_context=True, no_pm=False)
    @commands.has_role("tester")
    async def editurl(self, ctx, character : str, move : str, URL : str):
        """Please use the Imgur target as \"URL\". For example, in the 
           url https://i.imgur.com/2FFTv9.gif, the full command is
           ~smash editurl <character> <move> 2FFTv9"""
        try:
            char = self._get_character_name( character )
            atk = self._get_move( move )
            char_data = self._get_character_data( char )
        except KeyError as e:
            try:
                char = self._get_character_name( move )
                atk = self._get_move( character )
                move = character
                char_data = self._get_character_data(char)
            except KeyError as e:
                print(e)
                return
            print(e)
        if "Total frames" in char_data[atk]:
            if "Hits" in atk_data:
                char_data[atk]["URL"] = URL
                self._save_char(char, char_data)
                await self.bot.say("Saved")
        else:
            await self.bot.say("This move has complex attributes, pick one of the following:")
            choices = ""
            for key in char_data[atk]:
                choices += key+" "
            await self.bot.say(choices)
            try:
                answer = await self.bot.wait_for_message(timeout=60, author=ctx.message.author)
                answer = answer.content
            except:
                await self.bot.edit_message(msg, "Subcommand editurl has timed out.")
                return
            if answer in char_data[atk]:
                char_data[atk][answer]["URL"] = URL
                self._save_char(char, char_data)
                await self.bot.say("Saved")
            else:
                await self.bot.say("Couldn't find that attribute.")

    @commands.group(pass_context=True, no_pm=False, aliases=['fuck','f'], invoke_without_command=True)
    async def screw(self, ctx, *, character : str):
        """Returns a random \"fact\" about a character."""
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self._screw, character=character)

    # Actually returns the complaint to the channel
    @screw.command(pass_context=True, no_pm=True, hidden=True)
    async def _screw(self, ctx, *, character):
        try:
            char = self._get_character_name(character)
        except:
            return
        info = self._get_privilege(char)
        if info["complaints"]:
            complaint = random.choice(info["complaints"])
            await self.bot.say("Screw "+char+"...\n"+complaint["entry"])
        else:
            await self.bot.say("Nobody has complained about "+char+" yet. I guess they're fair and balanced?")

    @screw.command(name="add", pass_context=True, no_pm=False)
    async def add_complaint(self, ctx, *, character : str):
        """Tries to add a complaint to a character."""
        try:
            char = self._get_character_name(character)
        except:
            return
        msg = await self.bot.say("I'm listening. Accepting a complaint for "+char+"...")
        try:
            answer = await self.bot.wait_for_message(timeout=60, author=ctx.message.author)
            answer = answer.content
        except:
            await self.bot.edit_message(msg, ":/ Sorry, I got bored and stopped listening... (complaints time out after 60 seconds!)")
            return
        info = self._get_privilege(char)
        self.privilege[char]["complaints"].append( { "entry" : answer } )
        self._save_privilege()
        await self.bot.edit_message(msg, "Got it. I didn't realize you feel that way about "+char+".")

    @commands.group(pass_context=True, no_pm=False, aliases=['dyk'], invoke_without_command=True)
    async def fact(self, ctx, *, character : str):
        """Returns a random fact about a character."""
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self._fact, character=character)

    # Actually return the fact to the channel
    @fact.command(pass_context=True, no_pm=True, hidden=True)
    async def _fact(self, ctx, *, character):
        try:
            char = self._get_character_name(character)
        except:
            return
        info = self._get_privilege(char)
        if info["facts"]:
            fact = random.choice(info["facts"])
            await self.bot.say("Did you know...\n"+fact["entry"])
        else:
            await self.bot.say("Hmm, I don't know anything about "+char+" yet. You should ~fact add "+char+" and change that!")

    @fact.command(name="add", pass_context=True, no_pm=False)
    async def add_fact(self, ctx, *, character : str):
        """Tries to add a fact about a character."""
        try:
            char = self._get_character_name(character)
        except:
            return
        msg = await self.bot.say("I'm listening. Tell me something about "+char+"...")
        try:
            answer = await self.bot.wait_for_message(timeout=60, author=ctx.message.author)
            answer = answer.content
        except:
            await self.bot.edit_message(msg, "I didn't catch that... I can't wait for more than a minute. Try again?")
            return
        info = self._get_privilege(char)
        self.privilege[char]["facts"].append( { "entry" : answer } )
        self._save_privilege()
        await self.bot.edit_message(msg, "Got it. Good to know, thanks.")

def check_folders():
    if not os.path.exists(RESOURCES):
        print("Creating smashing data folder...")
        os.makedirs(RESOURCES)

def check_files():
    garpr = RESOURCES+"garpr_rankings.json"
    melee = RESOURCES+"frames/melee/"
    files = [RESOURCES+"character_privilege.json", garpr]
    for path in files:
        if not dataIO.is_valid_json(path):
            print("Creating empty "+str(path)+"...")
            dataIO.save_json(path, {})    

def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Helper(bot, RESOURCES))
