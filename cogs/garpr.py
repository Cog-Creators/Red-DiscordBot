# GarPR integration cog for Red-DiscordBot by Twentysix, an
#   open-source discord bot (github.com/Cog-Creators/Red-DiscordBot)
#
# Authored by Swann (github.com/swannobi)
# GarPR at github.com/garsh0p/garrpr
#
# Route class based on martmists' work on the ram.moe wrapper
#
# Last updated Nov 15, 2017

import discord
import os
import re
import requests
from discord.ext import commands
from cogs.utils.dataIO import dataIO
from copy import deepcopy
from .utils import checks
from __main__ import send_cmd_help
import urllib
from types import SimpleNamespace

class GarPR:
    """Contains most smash-based static commands"""

    def __init__(self, bot, resources_folder):
        self.bot = bot
        # Resources
        self.resources = resources_folder
        self.settings = dataIO.load_json(self.resources+"garpr_settings.json")
        self.rankings_uri = self.settings["region"]+"/rankings"
        self.players_uri = self.settings["region"]+"/players"
        self.matches_uri = self.settings["region"]+"/matches/"
        self.tournaments_uri = self.settings["region"]+"/tournaments"
        self.url = "https://www.notgarpr.com/#/"
        self.data_url = "https://www.notgarpr.com:3001/"
        # Determine if rankings should be reloaded
        if not self._checkgar():
            # Load cached resources
            self.rankings_cache = dataIO.load_json(self.resources+"garpr_rankings.json")
            self.matchup_cache = dataIO.load_json(self.resources+"garpr_match_records.json")
            self.players = dataIO.load_json(self.resources+"garpr_players.json")
        # Set default garpr rank emotes
        self.rank_emotes = self.settings["rank emotes"]

    def _checkgar(self):
        """Queries the regional garpr and checks if there have been any new tournaments logged 
        since the last time it checked.

        If so, it invalidates the cache and updates players/match records data."""
        actualTournies = len(Route(base_url=self.data_url, path=self.tournaments_uri).sync_query()["tournaments"])
        if( actualTournies != self.settings["tournaments on record"] ):
            # Invalidate cached resources
            self._refresh_cog()
            self.matchup_cache = {}
            self.settings["tournaments on record"] = actualTournies
            dataIO.save_json(self.resources+"garpr_settings.json", self.settings)
            dataIO.save_json(self.resources+"garpr_match_records.json", self.matchup_cache)
            return True
        return False
    
    def _refresh_cog(self):
        """Attempt to sync the bot with the actual GarPR."""
        try:
            self.players = Route(base_url=self.data_url,path=self.players_uri).sync_query()
            self.rankings_cache = Route(base_url=self.data_url,path=self.rankings_uri).sync_query()
            dataIO.save_json(self.resources+"garpr_players.json", self.players)
            dataIO.save_json(self.resources+"garpr_rankings.json", self.rankings_cache)
        except ResponseError as e:
            print("Couldn't properly refresh garpr. Some commands may not work as expected.")
            print(e)

    def _get_rankings(self):
        try:
            return deepcopy(self.rankings_cache["ranking"])
        except:
            print("Helper.py: something went wrong when copying self.rankings_cache")

    async def _get_player_stats(self, playerid : str):
        """Do the http call to garpr for some playerdata."""
        match_records = deepcopy(self.matchup_cache)
        # If player match data exists in the in-memory cache, return it
        if playerid in match_records:
            return match_records[playerid]
        # Otherwise, get it, store it in the cache
        playerdata = Route(base_url=self.data_url,path=self.matches_uri+playerid).sync_query()
        self.matchup_cache[playerid] = playerdata
        dataIO.save_json(self.resources+"garpr_match_records.json", self.matchup_cache)
        return playerdata

    def _get_playerid(self, player : str):
        """Checks for a player in the cache, given a playername."""
        for entry in self.players["players"]:
            if player.lower() == entry["name"].lower():
                return entry
        raise KeyError("Player not found: "+player)

    @commands.command(pass_context=False, no_pm=True)
    async def checkgar(self):
        """Attempts to synchronize the bot with the data in garpr."""
        if self._checkgar():
            await self.bot.say("There were new tournaments... I just refreshed the cache. Data is synced now!")
        else:
            await self.bot.say("No new tournaments.")

    @commands.command(pass_context=True, no_pm=False)
    async def stats(self, ctx, *, player : str):
        """Gets garpr tournament statistics for a player.
        
        Use ~stats <player1> VS <player2> to get historical matchup stats, if they exist.

        Be aware that GarPR is created with in-state players in mind. If you want to check
        the match history of an in-state player vs an out-of-state player, the in-state
        player should be listed FIRST.
        """
        # Parse the parameter for any occurance of a delimiter ("vs"), 
        #  which would make this a pvp stats query.
        if any(delim in player.lower() for delim in [" vs ", " vs. ", " versus "]):
            # Grab the two players' names
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
                        matchup.last_played = match["tournament_date"]
                if not matchup.since:
                    await self.bot.say("No data for "+p1+"/"+p2+". Use ~stats for more info.")
                    return
            except KeyError as e:
                print(e)
                return
            message = p1+" is ("+str(matchup.wins)+"-"+str(matchup.losses)+") vs "+p2+", since "+str(matchup.since)+"."
            if matchup.last_tournament:
                message += "\nThey last played at "+matchup.last_tournament+" ("+matchup.last_played+")."
            await self.bot.say(message)
            return
        # Since no delimiter was present, this is a single-player stats query.
        try:
            stats = await self._get_player_stats( self._get_playerid( player )["id"] )
            # The PPMD Contingency
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
            await self.bot.say(self.url+self.rankings_uri)
        else:
            try:
                playerinfo = self._get_playerid( player )
            except KeyError as e:
                print(e)
                return
            stats = await self._get_player_stats( playerinfo["id"] )
            rating = playerinfo["ratings"][self.settings["region"]]["mu"]
            sigma = playerinfo["ratings"][self.settings["region"]]["sigma"]
            data = discord.Embed(title=playerinfo["name"], url=self.url+self.players_uri+"/"+playerinfo["id"])
            # Sorry for the magic numbers. This is just how garpr calculates the adjusted
            #  rating behind the scenes. Since it only exposes the unadjusted ratings, we
            #  have do to this calculation on the fly.
            data.add_field(name="Adjusted rating:", value="*_"+str(round(rating-(3*sigma), 3))+"_*")
            for guy in self._get_rankings():
                # Only add the rank field if the player is, indeed, ranked
                if guy["name"] == playerinfo["name"]:
                    data.add_field(name="rank", value=guy["rank"])
                    if 1 == guy["rank"]:
                        data.colour = self.settings["rank colors"][0]
                        data.set_field_at(index=1, name="Rank:", value=str(guy["rank"])+self.settings["rank emotes"][0])
                    elif 1 < guy["rank"] < 11:
                        data.colour = self.settings["rank colors"][1] 
                        data.set_field_at(index=1, name="Rank:", value=str(guy["rank"])+self.settings["rank emotes"][1])
                    elif 11 <= guy["rank"] < 26:
                        data.colour = self.settings["rank colors"][2]
                        data.set_field_at(index=1, name="Rank:", value=str(guy["rank"])+self.settings["rank emotes"][2])
                    elif 26 <= guy["rank"] < 51:
                        data.colour = self.settings["rank colors"][3]
                        data.set_field_at(index=1, name="Rank:", value=str(guy["rank"])+self.settings["rank emotes"][3])
                    elif 51 <= guy["rank"] < 101:
                        data.colour = self.settings["rank colors"][4]
            data.set_footer(text="notgarpr-discord integration by Swann")
            try:
                await self.bot.say(embed=data) 
            except discord.HTTPException:
                await self.bot.say("I need the embed links permission :(")

    @commands.group(pass_context=True, no_pm=True)
    @checks.mod_or_permissions()
    async def garprset(self, ctx):
        """Changes the settings for retrieving data from GarPR"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    @garprset.command(pass_context=True)
    async def region(self, ctx, state : str):
        """Sets the state for GarPR. Must match the GarPR URI exactly (e.g. "Central Florida" region is "cfl")."""
        self.settings["region"] = state
        dataIO.save_json(self.resources+"garpr_settings.json", self.settings)
        # Invalidate all local caches
        await self.bot.say("Set new region: "+state+", refreshing data now...")
        await self._refresh_cog()

    @garprset.command(pass_context=True)
    async def icon(self, ctx):
        """Sets the icons that display next to GarPR ranked (top 100) players."""
        tiers = ["Rank 1", "Rank 2-10", "Rank 11-25", "Rank 26-50", "Rank 51-100"]
        prompt = await self.bot.say("Current settings:\n(1) "+tiers[0]+" "+self.settings["rank emotes"][0]
                +"\n(2) "+tiers[1]+" "+self.settings["rank emotes"][1]
                +"\n(3) "+tiers[2]+" "+self.settings["rank emotes"][2]
                +"\n(4) "+tiers[3]+" "+self.settings["rank emotes"][3]
                +"\n(5) "+tiers[4]+" "+self.settings["rank emotes"][4]
                +"\nFrom above, choose an option 1-5 to change!")
        try:
            answer = await self.bot.wait_for_message(timeout=60, author=ctx.message.author)
            answer = int(re.sub(r'[^\d]', '', answer.content))
            if answer < 0 or answer > 5:
                await self.bot.edit_message(prompt, "Invalid choice")
                return
            await self.bot.edit_message(prompt, "Editing emote for ("+tiers[answer-1]+")\nWhich emote should display?")
            emote = await self.bot.wait_for_message(timeout=60, author=ctx.message.author)
            emote = emote.content
        except:
            await self.bot.edit_message(prompt, "Timed out.")
            return
        self.settings["rank emotes"][answer-1] = emote
        dataIO.save_json(self.resources+"garpr_settings.json", self.settings)
        await self.bot.edit_message(prompt, "Ok, I've set "+emote+" as the new rank icon for"+str(answer))

    @garprset.command(pass_context=True, name="color")
    async def color(self, ctx):
        """Sets the color of the Embed for GarPR ranked (top 100) players.
        
        Use a site like color-hex to pick colors. Hex codes will be translated
        into discord-compatible colors and shown via an example role."""
        tiers = ["Rank 1", "Rank 2-10", "Rank 11-25", "Rank 26-50", "Rank 51-100"]
        roles = ctx.message.server.roles
        roleNames = []
        coloredRoles = [0,1,2,3,4]
        msg = "Current settings:\n"
        for role in roles:
            roleNames.append(role.name)
        for index, botRole in enumerate(tiers):
            if botRole not in roleNames:
                try:
                    role = await self.bot.create_role(ctx.message.server, name=botRole, mentionable=True, colour=discord.Colour(self.settings["rank colors"][index]))
                except:
                    print("error creating "+botRole)
            else:
                await self.bot.edit_role(ctx.message.server, role=roles[roleNames.index(botRole)], colour=discord.Colour(self.settings["rank colors"][index]))
                role = roles[roleNames.index(botRole)]
            try:
                coloredRoles[index] = role
                msg+="\n("+str(index+1)+") "+role.mention
            except:
                print("error editing "+botRole)
        msg+="\nFrom above, choose an option 1-5 to change!"
        prompt = await self.bot.say(msg)

        try:
            answer = await self.bot.wait_for_message(timeout=60, author=ctx.message.author)
            answer = int(re.sub(r'[^\d]', '', answer.content))
            if answer < 0 or answer > 5:
                await self.bot.edit_message(prompt, "Invalid choice")
                return
            await self.bot.edit_message(prompt, "Editing color for "+coloredRoles[answer-1].mention+"\nWhich color should display? Use http://www.color-hex.com/ for help!")
            color = await self.bot.wait_for_message(timeout=60, author=ctx.message.author)
            color = re.sub("#", '', color.content)
        except:
            await self.bot.edit_message(prompt, "Timed out.")
            return
        try:
            self.settings["rank colors"][answer-1] = int(color, 16)
            await self.bot.edit_role(ctx.message.server, role=coloredRoles[answer-1], colour=discord.Colour(self.settings["rank colors"][answer-1]))
        except BaseException as e:
            await self.bot.edit_message(prompt, "Encountered an error while editing color... sorry :(")
            print(e)
            return
        dataIO.save_json(self.resources+"garpr_settings.json", self.settings)
        await self.bot.edit_message(prompt, "Ok, I've set the new color for "+coloredRoles[answer-1].mention)

# Handles request routing
class Route:
    def __init__(self, base_url, path, headers=None, method="GET"):
        self.base_url = base_url
        self.path = path
        self.headers = headers
        self.method = method
    def sync_query(self, url_params=None):
        result = getattr( requests, self.method.lower() )(
                self.base_url+self.path, headers=self.headers)
        if 200 <= result.status_code < 300:
            return result.json()
        else:
            raise ResponseError("Got an unsuccessful response code: {}, from {}".format(result.status_code, self.base_url+self.path))

    def __call__(self, url_params=None):
        return self.sync_query(url_params)

class ResponseError(BaseException):
    pass

def check_folders(resources_folder):
    if not os.path.exists(resources_folder):
        print("Creating smashing data folder...")
        os.makedirs(resources_folder)

def check_files(resources_folder):
    garpr = resources_folder+"garpr_rankings.json"
    records = resources_folder+"garpr_match_records.json"
    settings = resources_folder+"garpr_settings.json"
    if not dataIO.is_valid_json(garpr):
        print("Creating empty "+str(garpr)+"...")
        dataIO.save_json(garpr, {})
    if not dataIO.is_valid_json(records):
        print("Creating empty "+str(records)+"...")
        dataIO.save_json(records, {})
    if not dataIO.is_valid_json(settings):
        print("Creating default "+str(settings)+"...")
        dataIO.save_json(settings, 
                {
                    "region" : "northcarolina",
                    "tournaments on record" : 0,
                    "rank emotes" : [":pineapple:", ":apple:", ":tangerine:", ":cherries:"],
                    "rank colors" : [discord.Colour.dark_green().value,discord.Colour.gold().value,discord.Colour.light_grey().value,discord.Colour.purple().value,10061926]
                })

def setup(bot):
    resources_folder = "data/smashing/"
    check_folders(resources_folder)
    check_files(resources_folder)
    bot.add_cog(GarPR(bot, resources_folder))
