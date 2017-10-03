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
STATE = "northcarolina" 

class Helper:
    """Contains most smash-based static commands"""

    def __init__(self, bot, resources_folder):
        self.bot = bot
        self.melee_chars = dataIO.load_json(RESOURCES+"melee_chars.json")
        self.movelist = dataIO.load_json(RESOURCES+"movelist.json")
        self.privilege = dataIO.load_json(RESOURCES+"character_privilege.json")
        # notGARPR
        # TODO Store data in JSON (cache players, rankings, tournaments, and last 50 player match datasets)
        # TODO Reload players/rankings/tournaments data when the last tournaments.json != the last tournament from GarPR
        self.garpr.rankings_uri = STATE+"/rankings"
        self.garpr.players_uri = STATE+"/players"
        self.garpr.matches_uri = STATE+"/matches/"
        self.garpr.tournaments_uri = STATE+"/tournaments/"
        self.garpr.data_url = "https://www.notgarpr.com:3001/"
        self.garpr.players = Route(base_url=self.garpr.data_url,path=self.garpr.players_uri).sync_query()
        self.garpr.rankings = Route(base_url=self.garpr.data_url,path=self.garpr.rankings_uri).sync_query()
#        self.garpr.tournaments = Route(base_url=self.garpr.data_url,path=self.garpr.tournaments_uri).sync_query()
#        self.garpr.rankings = dataIO.load_json(RESOURCES+"garpr_rankings.json")
#        self.gatpr.players = dataIO.load_json(RESOURCES+"garpr_player_records.json")
        self.garpr.url = "https://www.notgarpr.com/#/"

    def _get_move(self, move):
        try:
            move = self.movelist[re.sub(r"\s", "", move.lower())]
            movedata = dataIO.load_json(RESOURCES+"frames/melee/"+move+".json")
            return movedata
        except:
            raise KeyError("Couldn't find the move {}.".format(str(move)))

    def _get_rankings(self):
        try:
            return deepcopy(self.rankings["ranking"])
        except:
            print("Helper.py: something went wrong when copying self.rankings")

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

    def _get_character(self, character):
        try:
            return self.melee_chars[re.sub(r"\s", "", character.lower())]
        except:
            raise KeyError("Couldn't find the character {}.".format(str(character)))

    def _save_privilege(self):
        dataIO.save_json(RESOURCES+"character_privilege.json", self.privilege)
    
    async def _get_player_stats(self, playerid : str):
        return Route(base_url=self.garpr.data_url,path=self.garpr.matches_uri+playerid).sync_query()

    def _get_playerid(self, player : str):
        for entry in self.garpr.players["players"]:
            if player.lower() == entry["name"].lower():
                return entry
        raise KeyError("Player not found: "+player)

    @commands.command(pass_context=True, no_pm=False)
    async def stats(self, ctx, *, player : str):
        """Gets garpr tournament statistics for a player.
        
        Use ~stats <player1> VS <player2> to get historical matchup stats, if they exist.

        Be aware that GarPR is created with NC players in mind. If you want to check
        the match history of an NC player vs an out-of-state player, the NC player should
        be listed FIRST.
        """
        if any(delim in player for delim in [" vs ", " VS ", " vs. ", " VS. ", " Vs. ", " Vs "]):
            p1,p2 = re.sub(r"( vs\. | VS\. | VS )", " vs ", player).split(" vs ")
            try:
                p1_info = self._get_playerid( p1 )
                p1_matches = await self._get_player_stats( p1_info["id"] )
                matchup = SimpleNamespace()
                matchup.wins = matchup.losses = 0
                matchup.last_tournament = None
                matchup.since = None
                for match in p1_matches["matches"]:
                    if match["opponent_name"].lower() == p2.lower():
                        if not matchup.since:
                            matchup.since = match["tournament_date"]
                        if match["result"] == "win":
                            matchup.wins += 1
                        else:
                            matchup.losses += 1
                        matchup.last_tournament = match["tournament_name"]
                if not matchup.since:
                    await self.bot.say("No data for "+p1+"/"+p2+". Use ~stats for more info.")
                    return
            except KeyError as e:
                print(e)
                return
            message = p1+" is ("+str(matchup.wins)+"-"+str(matchup.losses)+") vs "+p2+", since "+str(matchup.since)+"."
            if matchup.last_tournament:
                message += "\nThey last played at "+matchup.last_tournament+"."
            await self.bot.say(message)
            return
        try:
            stats = await self._get_player_stats( self._get_playerid( player )["id"] )
            if stats["losses"] == 0:
                ratio = "∞"
            else:
                ratio = str(round(stats["wins"]/stats["losses"], 3))
            await self.bot.say("I can see "+player+" has "+str(len(stats["matches"]))+" match "
            "records, since "+stats["matches"][0]["tournament_date"]+"\n"
            "This player has "+str(stats["wins"])+" wins "
            "and "+str(stats["losses"])+" losses ("+ratio+")")
        except KeyError as e:
            print(e)

    @commands.command(pass_context=True, no_pm=True)
    async def garpr(self, ctx, *, player : str=None):
        """Returns the state garpr, or the ranking for a particular player."""
        if not player:
            await self.bot.say(self.garpr.url+self.garpr.rankings_uri)
        else:
            playerinfo = self._get_playerid( player )
            stats = await self._get_player_stats( playerinfo["id"] )
            rating = playerinfo["ratings"][STATE]["mu"]
            sigma = playerinfo["ratings"][STATE]["sigma"]
            data = discord.Embed(title=playerinfo["name"], url=self.garpr.url+self.garpr.players_uri+"/"+playerinfo["id"])
            data.add_field(name="Adjusted rating:", value="*_"+str(round(rating-(3*sigma), 3))+"_*")
            for guy in self.garpr.rankings["ranking"]:
                if guy["name"] == playerinfo["name"]:
                    data.add_field(name="rank", value=guy["rank"])
                    if 1 == guy["rank"]:
                        data.colour = discord.Colour.dark_green()
                        data.set_field_at(index=1, name="Rank:", value=str(guy["rank"])+"<:champion:261390756898537473>")
                    elif 1 < guy["rank"] < 11:
                        data.colour = discord.Colour.gold()
                        data.set_field_at(index=1, name="Rank:", value=str(guy["rank"])+":fire:")
                    elif 11 <= guy["rank"] < 26:
                        data.colour = discord.Colour.light_grey()
                        data.set_field_at(index=1, name="Rank:", value=str(guy["rank"])+"<:Melee:260154755706257408>")
                    elif 26 <= guy["rank"] < 51:
                        data.colour = discord.Colour.purple()
                        data.set_field_at(index=1, name="Rank:", value=str(guy["rank"])+":ok_hand:")
                    elif 51 <= guy["rank"] < 101:
                        data.colour = discord.Colour(0x998866)
            data.set_footer(text="notgarpr-discord integration by Swann")
            await self.bot.say(embed=data)

    @commands.group(pass_context=True, no_pm=True)
    @checks.mod_or_permissions()
    async def smash(self, ctx):
        """Changes smash module settings"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @smash.command(pass_context=True, no_pm=False)
    @checks.is_owner()
    async def frames(self, ctx, character : str, move : str):
        """Retrieve the frame data and gfy for a move"""
        try:
            char = self._get_character( character )
            atk_data = self._get_move( move )[char]
        except:
            # Catch and fix swapped order of character and move
            try:
                char = self._get_character( move )
                atk_data = self._get_move( character )[char]
                move = character
            except KeyError as e:
                print(e)
                return
        print(atk_data)
        required = ["Total Frames", "SAF", "Hits"]
        data = discord.Embed(title="__Frame data and animation for: "+char+"'s "+move+"__")
        data.set_image(url=atk_data["URL"])
        for field in required:
            data.add_field(name=field, value=atk_data[field], inline=True)
        required.append("URL")
        for key in atk_data:
            if key not in required:
                data.add_field(name=key, value=atk_data[key], inline=True)
        data.set_footer(text="plugin by Swann, data by Stratocaster and SDM")
        await self.bot.say(embed=data)
        

    @commands.group(pass_context=True, no_pm=False, aliases=['fuck','f'], invoke_without_command=True)
    async def screw(self, ctx, *, character : str):
        """Returns a random \"fact\" about a character."""
        if ctx.invoked_subcommand is None:
            await ctx.invoke(self._screw, character=character)

    # Actually returns the complaint to the channel
    @screw.command(pass_context=True, no_pm=True, hidden=True)
    async def _screw(self, ctx, *, character):
        try:
            char = self._get_character(character)
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
            char = self._get_character(character)
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
            char = self._get_character(character)
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
            char = self._get_character(character)
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
    files = [RESOURCES+"character_privilege.json", melee+"chars.json", melee+"jab.json", melee+"da.json", melee+"grab.json", melee+"dtilt.json", melee+"ftilt.json", melee+"utilt.json",melee+"dsmash.json",melee+"fsmash.json",melee+"usmash.json",melee+"nair.json",melee+"dair.json",melee+"fair.json",melee+"uair.json",melee+"bair.json", garpr]
    for path in files:
        if not dataIO.is_valid_json(path):
            print("Creating empty "+str(path)+"...")
            dataIO.save_json(path, {})    

def setup(bot):
    check_folders()
    check_files()
    bot.add_cog(Helper(bot, RESOURCES))
