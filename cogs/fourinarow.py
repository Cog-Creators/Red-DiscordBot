from .utils.dataIO import fileIO
from .utils import checks
from __main__ import send_cmd_help
from __main__ import settings as bot_settings
# Sys.
import discord
from discord.ext import commands
from operator import itemgetter, attrgetter
from copy import deepcopy
import random
import os
import sys
import time
import logging

__author__ = "Controller Network"
__version__ = "1.0.0"

#TODO:
#   Finish addbot player: Disabled by default.
#   Cleanup some more, look for inefficient code, double checks etc..

DIR_DATA = "data/fourinarow"
GAMES = DIR_DATA+"/games.json"
SETTINGS = DIR_DATA+"/settings.json"
PLAYERS = DIR_DATA+"/players.json"
STATS = DIR_DATA+"/stats.json"
LOGGER = DIR_DATA+"/fourinarow.log"
BACKUP = DIR_DATA+ "/players.backup"

class FourInARow:
    """Four in a row
    Dominate the board!"""

    def __init__(self, bot):
        self.bot = bot
        self.game = fileIO(GAMES, "load")
        self.settings = fileIO(SETTINGS, "load")
        self.players = fileIO(PLAYERS, "load")
        self.stats = fileIO(STATS, "load")
        self.BOARD_HEADER = self.settings["BOARD_HEADER"]
        self.ICONS = self.settings["ICONS"]
        self.TOKENS = self.settings["TOKENS"]
        self.EMPTY = self.settings["ICONS"][0][0]
        self.PREFIXES = bot_settings.prefixes

    @commands.group(name="4row", pass_context=True)
    async def _4row(self, ctx):
        """Four in a row game operations."""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return

    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Game Operations
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    @_4row.command(pass_context=True, no_pm=True)
    async def register(self, ctx):
        """Registers an 'Four in a row' account."""
        user = ctx.message.author
        if self.account_check(user.id) is False:
            registerData = await self.register_player(ctx, user)# returns {"showMsg": bool, "msg": str} 
            if registerData["showMsg"]:
                await self.bot.say(registerData["msg"])      
        else:
            await self.bot.say("{}` You are already registered!` ".format(user.mention))

    @_4row.command(pass_context=True, no_pm=True)
    async def new(self, ctx):
        """Create a new game."""
        user = ctx.message.author
        if self.account_check(user.id):
            if ctx.message.channel.id not in self.game["CHANNELS"]:
                now = round(time.time())
                # Set-up a game.
                self.game["CHANNELS"][ctx.message.channel.id] = {"board": self.empty_board(0), 
                                                                                        "boardSize": 0, 
                                                                                        "activePlayers": 0 ,
                                                                                        "PLAYERS": {"IDS": [], "NAMES": [], "TOKENS": []},
                                                                                        "VOTES_STP": {"votes": 0, "voteIds": []}, 
                                                                                        "turnIds": [],
                                                                                        "skipIds": [], 
                                                                                        "inQue": "yes",
                                                                                        "deleteMsg": True,
                                                                                        "gameStarted": now, 
                                                                                        "lastActivity": now, 
                                                                                        "botDifficulty": self.settings["BOT_SETTINGS"]["DEFAULT_DIFFICULTY"], 
                                                                                        "winner": "unknown"}
                fileIO(GAMES, "save", self.game)
                joinData = await self.join_game(ctx, user)# returns {"delMsg": bool, "showMsg": bool, "drawBoard": bool, "msg": str}
                if joinData["delMsg"]:
                    await self.delete_message(ctx)
                if joinData["showMsg"] and not joinData["drawBoard"]:
                    await self.bot.say(joinData["msg"])
                elif joinData["showMsg"] and joinData["drawBoard"]:
                    await self.draw_board(ctx, joinData["msg"])
            else:
                await self.bot.say("{}` There is already a new game set!\nTry: '{}4row join'` ".format(user.mention, self.PREFIXES[0]))
        else:       
            await self.bot.say( "{} ` You need an account in order to use this command.\nType:'{}4row register' to create one`".format(user.mention, self.PREFIXES[0]))

    @_4row.command(pass_context=True, no_pm=True)
    async def start(self, ctx):
        """Start the game."""
        user = ctx.message.author
        BOARDWIDTH = self.settings["BOARDWIDTH"]
        try:
            BOARDSIZE = self.game["CHANNELS"][ctx.message.channel.id]["boardSize"]
            activePlayers = self.game["CHANNELS"][ctx.message.channel.id]["activePlayers"]
            data = True
        except Exception as e:
            data = False
        if data:
            if not self.ingame_check(ctx, user.id):
                await self.bot.say( "{} ` You need to be in a game to start.`".format(user.mention))
                return
            elif activePlayers <= 1:
                await self.bot.say( "{} ` There must be at least on more player to start this game.`".format(user.mention))
                return
            elif self.ingame_check(ctx, user.id):
                await self.start_game(ctx, user.id)
                await self.delete_message(ctx)           
                await self.draw_board(ctx, "\n` Game started\nIf it's your turn use '{}mytoken [number 1/{}]`".format(self.PREFIXES[0], BOARDWIDTH[BOARDSIZE]))
        else:
            await self.bot.say( "{} ` No game to start.`".format(user.mention))                

    @_4row.command(pass_context=True, no_pm=True)
    async def stop(self, ctx):
        """Stops the game by voting or after a game has been expired."""
        user= ctx.message.author
        Allowed = False
        if self.account_check(user.id):
            # Check for a game @ channel.
            try:
                now = round(time.time())
                CH_GAME = self.game["CHANNELS"][ctx.message.channel.id]
                activePlayers = CH_GAME["activePlayers"]
                chGamestarted = CH_GAME["gameStarted"]
                chLastActivity = CH_GAME["lastActivity"]
                CH_VOTES_STP = CH_GAME["VOTES_STP"]
                gameVoteUnlocks = self.settings["VOTE_UNLOCK_TIME"]
                gameExpires = self.settings["EXPIRE_TIME"]
                minVotesToUnlock = self.settings["MIN_VOTES_TO_UNLOCK"]
                differenceStarted = now-chGamestarted
                differenceLastActivity = now-chLastActivity
                data = True
            except Exception as e:
                logger.info(e)
                data = False
            if data:
                # User has voted already?
                if user.id not in CH_VOTES_STP["voteIds"] or differenceStarted >= gameExpires:
                    # Check if game is expired of stop voted.
                    if differenceStarted >= gameExpires:
                        await self.stop_game(ctx)
                        self.stats["gamesTimedOut"] += 1
                        fileIO(STATS, "save", self.stats)
                        await self.bot.say("{} ` Game stopped`".format(user.mention))
                        return
                    elif activePlayers <= 1: # If for any reason one player is left behind in an active game, allow a stop.
                        await self.stop_game(ctx)
                        self.stats["gamesStopped"] += 1
                        fileIO(STATS, "save", self.stats)
                        await self.bot.say("{} ` Game stopped`".format(user.mention))
                        return
                    else:# Not expired yet so check unlock votes.
                        # Game is unlocked?
                        if differenceLastActivity >= gameVoteUnlocks:
                            CH_VOTES_STP["votes"] += 1
                            CH_VOTES_STP["voteIds"].append(user.id)
                            await self.delete_message(ctx)
                            await self.draw_board(ctx, "\n` Votes to stop this game: {}/{}`".format(CH_VOTES_STP["votes"], minVotesToUnlock))
                            # Save vote.
                            self.game["CHANNELS"][ctx.message.channel.id]["VOTES_STP"] = CH_VOTES_STP
                            fileIO(GAMES, "save", self.game)
                        # Game is locked for vote?
                        elif differenceLastActivity < gameVoteUnlocks:
                            timeLeft = gameVoteUnlocks-differenceLastActivity
                            #await self.delete_message(ctx)
                            await self.bot.say("{} ` Game is locked by a last activity cool-down, please wait {}sec. to stop(vote) this game down.`"
                                                        .format(user.mention, timeLeft))
                        # Game has no lock conditions so output not expired message.
                        elif differenceStarted < gameExpires:
                            timeLeft = gameExpires-differenceStarted
                            #await self.delete_message(ctx)
                            await self.bot.say("{} ` Game is not expired yet, please wait {}sec. to stop this game, or start a game in another channel`"
                                                        .format(user.mention, timeLeft))
                        # Check votes to stop game before expire.
                        if CH_VOTES_STP["votes"] >= minVotesToUnlock:
                            await self.stop_game(ctx)
                            #await self.delete_message(ctx)
                            self.stats["gamesUnlocked"] += 1
                            fileIO(STATS, "save", self.stats)
                            await self.bot.say("` Game stopped\nWell done {}, you ruined the game...`".format(user))
                else: # user.id in CH_VOTES_STP["voteIds"]:
                    await self.bot.say( "{} ` You already voted.`".format(user.mention))         
            else:
                await self.bot.say( "{} ` No game to stop.`".format(user.mention))
        else:
            await self.bot.say( "{} ` You need an account in order to use this command.\nType:'{}4row register' to create one`".format(user.mention, self.PREFIXES[0]))

    @_4row.command(pass_context=True, no_pm=True)
    async def join(self, ctx):
        """Join a new game."""
        user = ctx.message.author
        try:
            inQue = self.game["CHANNELS"][ctx.message.channel.id]["inQue"]
            data = True
        except Exception as e:
            logger.info(e)
            data = False
        if data and inQue == "yes":
            joinData = await self.join_game(ctx, user)# returns {"delMsg": bool, "showMsg": bool, "drawBoard": bool, "msg": str}
            if joinData["delMsg"]:
                await self.delete_message(ctx)
            if joinData["showMsg"] and not joinData["drawBoard"]:
                await self.bot.say(joinData["msg"])
            elif joinData["showMsg"] and joinData["drawBoard"]:
                await self.draw_board(ctx, joinData["msg"])
        else:
            await self.bot.say("{} ` Nothing to join...`".format(user.mention))

    @_4row.command(pass_context=True, no_pm=True)
    async def leave(self, ctx):
        """Leave a game."""
        user = ctx.message.author
        try:
            inQue = self.game["CHANNELS"][ctx.message.channel.id]["inQue"]
            player = self.players["PLAYERS"][user.id]
            data = True
        except Exception as e:
            logger.info(e)
            data = False
        msg = ""
        if data and self.ingame_check(ctx, user.id):
            leaveData = await self.leave_game(ctx, user)# returns {"delMsg": bool, "showMsg": bool, "drawBoard": bool, "msg": str, "stopGame": bool}
            if leaveData["delMsg"]:
                await self.delete_message(ctx)
            if leaveData["showMsg"] and not leaveData["drawBoard"]:
                await self.bot.say(leaveData["msg"])
            elif leaveData["showMsg"] and leaveData["drawBoard"]:
                await self.draw_board(ctx, leaveData["msg"])
            if leaveData["stopGame"]:
                self.stats["gamesRuined"] += 1
                self.players["PLAYERS"][user.id]["STATS"]["wasted"] += 1
                self.players["PLAYERS"][user.id]["STATS"]["points"] += self.settings["REWARDS"]["RUIENING"]
                fileIO(PLAYERS, "save", self.players)
                fileIO(STATS, "save", self.stats)
                await self.stop_game(ctx)
        else:
            await self.bot.say("{} ` No game to leave from...`".format(user.mention))

    @_4row.command(pass_context=True, no_pm=True)
    async def board(self, ctx):
        """Displays the play field."""
        user = ctx.message.author
        await self.delete_message(ctx)
        await self.draw_board(ctx, "")

    @_4row.command(pass_context=True)
    async def score(self, ctx):
        """Shows your score."""
        user = ctx.message.author
        try:
            player = self.players["PLAYERS"][user.id]
            stats = player["STATS"]
            won = stats["won"] + stats["draw"]
            lost = stats["loss"] + stats["wasted"]
            data = True
        except Exception as e:
            logger.info(e)
            data = False
        if data and self.account_check(user.id):
            total = won+lost
            cTotal = total
            # Make cTotal = 1 for calc. if player is new/no games.
            if total == 0: cTotal = 1
            ratio = float(won)/(cTotal)
            resultRankings = await self.get_rankings(ctx, user.id)# Returns{"topScore": array, "userIdRank": string(userId)}
            userIdRank = resultRankings["userIdRank"]
            msg = "{}```\n".format(user.mention)
            msg ="{}You have played ({}) games, of those you won ({}), lost ({}), played ({}) even, and ruined ({}).\nThat gives you a win/loss ratio of: ({})\n\n".format(msg, 
                                                                                                                                                                                                                                        str(total),
                                                                                                                                                                                                                                        str(stats["won"]), 
                                                                                                                                                                                                                                        str(stats["loss"]), 
                                                                                                                                                                                                                                        str(stats["draw"]), 
                                                                                                                                                                                                                                        str(stats["wasted"]), 
                                                                                                                                                                                                                                        str(round(ratio, 2)))
            msg = "{}With an total of ({}) moves, the average time you need to make a move is ({}) seconds.\nThe average duration of a game you're part of is ({}) Minutes.\n\n".format(msg, 
                                                                                                                                                                                                                            str(stats["totalMoves"]), 
                                                                                                                                                                                                                            str(round(stats["averageTimeTurn"], 2)), 
                                                                                                                                                                                                                            str(round(stats["avarageTimeGame"]/60, 1)))
            msg = "{}That makes you “{}” with ({}) points, and places you on #({}) of in total ({}) registered players.```".format(msg, 
                                                                                                                                                                                str(player["MSG"]["joiningMsg"]), 
                                                                                                                                                                                str(stats["points"]), 
                                                                                                                                                                                str(userIdRank), 
                                                                                                                                                                                len(self.players["PLAYERS"]))
            await self.bot.say(msg)
        else:
            await self.bot.say( "{} ` You need an account in order to use this command.\nType:'{}4row register' to create one`".format(user.mention, self.PREFIXES[0]))

    @_4row.command(pass_context=True, no_pm=True)
    async def addbot(self, ctx):
        """Add a bot to the game in queue."""
        user = ctx.message.author
        bot = ctx.message.server.me
        try:
            inQue = self.game["CHANNELS"][ctx.message.channel.id]["inQue"]
            data = True
        except Exception as e:
            logger.info(e)
            data = False
        # Check permission.
        if self.account_check(user.id):
            if self.settings["BOT_SETTINGS"]["ENABLED"]:
                if data and inQue == "yes":
                    # Check is bot exist in players.
                    if not self.account_check(bot.id):
                        # Register bot
                        msg = await self.register_player(ctx, bot)# returns {"showMsg": bool, "msg": str}
                    # Check if account is made.
                    if self.account_check(bot.id):
                        joinData = await self.join_game(ctx, bot)# returns {"delMsg": bool, "showMsg": bool, "drawBoard": bool, "msg": str}
                        if joinData["delMsg"]:
                            await self.delete_message(ctx)
                        if joinData["showMsg"] and not joinData["drawBoard"]:
                            await self.bot.say(joinData["msg"])
                        elif joinData["showMsg"] and joinData["drawBoard"]:
                            await self.draw_board(ctx, joinData["msg"])
                    else:
                        await self.bot.say("{} ` Failed to add bot...`".format(user.mention))
                else:
                    await self.bot.say( "{} ` No game to join`".format(user.mention))
            else:
                await self.bot.say( "{} ` The use of a bot player is disabled`".format(user.mention))
        else:
            await self.bot.say( "{} ` You need an account in order to use this command`".format(user.mention))

    @_4row.command(pass_context=True, no_pm=True)
    async def kickbot(self, ctx):
        """Removes a bot from the game in queue."""
        user = ctx.message.author
        bot = ctx.message.server.me
        try:
            inQue = self.game["CHANNELS"][ctx.message.channel.id]["inQue"]
            data = True
        except Exception as e:
            logger.info(e)
            data = False
        # Check permission.
        if self.account_check(user.id):
            if self.settings["BOT_SETTINGS"]["ENABLED"]:
                if data and inQue == "yes":
                    # Check is bot exist in players.
                    if not self.account_check(bot.id):
                        # Register bot.
                        msg = await self.leave_game(ctx, bot)# returns {"msg": str} 
                    # Check if account is made.
                    if self.account_check(bot.id):
                        leaveData = await self.leave_game(ctx, bot)# returns {"delMsg": bool, "showMsg": bool, "drawBoard": bool, "msg": str, "stopGame": bool}
                        if leaveData["delMsg"]:
                            await self.delete_message(ctx)
                        if leaveData["showMsg"] and not leaveData["drawBoard"]:
                            await self.bot.say(leaveData["msg"])
                        elif leaveData["showMsg"] and leaveData["drawBoard"]:
                            await self.draw_board(ctx, leaveData["msg"])
                        if leaveData["stopGame"]:
                            await self.stop_game(ctx)
                    else:
                        await self.bot.say("{} ` Failed to remove bot...`".format(user.mention))
                else:
                    await self.bot.say( "{} ` No queue to leave from`".format(user.mention))
            else:
                await self.bot.say( "{} ` The use of a bot player is disabled`".format(user.mention))                  
        else:
            await self.bot.say( "{} ` You need an account in order to use this command.\nType:'{}4row register' to create one`".format(user.mention, self.PREFIXES[0]))

    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Direct Commands
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------         
            
    @commands.command(pass_context=True, no_pm=True)
    async def mytoken(self, ctx, someToken: int):
        """Insert token at given position."""
        user= ctx.message.author
        try:
            CH_GAME = self.game["CHANNELS"][ctx.message.channel.id]
            inQue = CH_GAME["inQue"]
            BOARDWIDTH = self.settings["BOARDWIDTH"]
            BOARDSIZE = CH_GAME["boardSize"]
            CH_PLAYERS = CH_GAME["PLAYERS"]
            skipIds = CH_GAME["skipIds"]
            data = True
        except Exception as e:
            logger.info(e)
            data = False
        if data and inQue == "no":
            if user.id not in skipIds:
                if await self.my_turn(ctx, user.id) == True:
                    tokenRow = None
                    freePos = None
                    stopGame = False
                    tokenRow = int(someToken)
                    tokenRow -= 1 # Index = 0/BOARDWIDTH
                    # Check if token is in range.
                    if tokenRow >= 0 and tokenRow <= BOARDWIDTH[BOARDSIZE]-1:
                        board = self.game["CHANNELS"][ctx.message.channel.id]["board"]
                        freePos = self.lowest_empty_space(ctx, tokenRow)
                        if freePos == -1:
                            await self.bot.say("\n{} ` Try another row.`".format(user.mention))
                        else:
                            await self.make_move(ctx, user, tokenRow, freePos)
                            commentList = ["\n ` Take your time.`", 
                                                "\n `This game is driven by the MARViN-DiscordBot`"]
                            comment = random.choice(commentList)
                            if len(CH_PLAYERS["IDS"]) >= 1:
                                for usr in range (len(CH_PLAYERS["IDS"])):
                                    if self.board_full(ctx):
                                        comment = ("\n{} ` It's a tie!     `".format(user.mention))
                                        self.game["CHANNELS"][ctx.message.channel.id]["winner"] = "draw"# Needed for update_score.
                                        await self.update_score(ctx)# Update score of all players.
                                        stopGame = True
                                    elif self.is_winner(ctx, self.TOKENS[CH_PLAYERS["TOKENS"][usr]][0]):
                                        comment = ("\n{} ` Owns this game with his {}'s`{}".format(user.mention, 
                                                                                                                                self.TOKENS[CH_PLAYERS["TOKENS"][usr]][0], 
                                                                                                                                self.TOKENS[CH_PLAYERS["TOKENS"][usr]][1]))
                                        self.game["CHANNELS"][ctx.message.channel.id]["winner"] = user.id# Needed for update_score.
                                        await self.update_score(ctx)# Update score of all players.
                                        stopGame = True
                                fileIO(GAMES, "save", self.game)
                            await self.delete_message(ctx)
                            await self.draw_board(ctx, comment)
                            # If game needs to be stopped by above conditions.
                            if stopGame == True:
                                comment = "\n{} `Congratulations, you owned the game with your {}'s`{}".format(user.mention,
                                                                                                                                                    self.TOKENS[CH_PLAYERS["TOKENS"][usr]][0], 
                                                                                                                                                    self.TOKENS[CH_PLAYERS["TOKENS"][usr]][1])
                                await self.draw_board(ctx, comment, True)# Dm board to user.
                                await self.bot.say("` Game ended`")
                                await self.stop_game(ctx)
                    else:
                        await self.bot.say("{} ` '{}mytoken [number 1/{}]'`".format(user.mention, self.PREFIXES[0], BOARDWIDTH[BOARDSIZE]))
                else:
                    await self.bot.say("{} ` Wait for your turn!`".format(user.mention))
            else:
                await self.bot.say("{} ` You left the game, you idiot!`".format(user.mention))
        else:
            await self.bot.say("{} ` Game not available or started.`".format(user.mention))
        
    @commands.command(pass_context=True, no_pm=True)
    async def setmytoken(self, ctx, newToken : int):
        """Change your preferred token."""
        user= ctx.message.author
        if self.account_check(user.id):
            max = len(self.settings["TOKENS"])-1# 0 is reserved for sys
            if newToken >= 1 and newToken <= max:
                msg = await self.token_switch(ctx, user, newToken)
                try:
                    inQue = self.game["CHANNELS"][ctx.message.channel.id]["inQue"]
                    data = True
                except Exception as e:
                    logger.info(e)
                    data = False
                if data and inQue == "yes" and user.id in self.game["CHANNELS"][ctx.message.channel.id]["PLAYERS"]["IDS"]:
                    await self.delete_message(ctx)
                    await self.draw_board(ctx, msg)
                else:
                    await self.bot.say("{}".format(msg))
            else:
                await self.bot.say("{} ` Choose a token number between 0 and {}, check DM for available tokens`".format(user.mention, max))
                msg = await self.msg_available_tokens()
                await self.bot.send_message(ctx.message.author, msg)
        else:
            await self.bot.say( "{} ` You need an account in order to use this command.\nType:'{}4row register' to create one`".format(user.mention, self.PREFIXES[0]))

    @commands.command(pass_context=True, no_pm=True)
    async def listtokens(self, ctx):
        """Shows the avaiable Tokens."""
        user= ctx.message.author
        await self.bot.say("{} ` Check DM for available tokens.`".format(user.mention))
        msg = await self.msg_available_tokens()
        await self.bot.send_message(ctx.message.author, msg)

    @_4row.command(name="leaderboard", pass_context=True)#Conflict's with Economy, so it became sub command.
    async def _leaderboard(self, ctx, page: int=-1):
        """Shows the 'Four in a row' leaderboard."""
        user = ctx.message.author
        page -= 1
        try:
            resultRankings = await self.get_rankings(ctx, user.id)# Returns{"topScore": array(userId/Score), "userIdRank": string(userId)}
            topScore = resultRankings["topScore"]
            userIdRank = resultRankings["userIdRank"]
            playerAmount = len(self.players["PLAYERS"])
            data = True
        except Exception as e:
            logger.info(e)
            data = False
        # Put players and their earned points in to a table.
        msgHeader = "{}\n```erlang\nPosition |   Username                          |  Score\n---------------------------------------------------------\n".format(user.mention)
        if data and playerAmount >= 1:
            await self.delete_message(ctx)
            pages = []
            totalPages = 0
            usr = 0
            userFound = False
            userFoundPage = False
            msg = ""
            while (usr < playerAmount):
                w=usr+10
                while (w > usr):
                    if usr >= playerAmount:
                        break
                    ul = len(topScore[usr][2])
                    sp = '                                 '# Discord username max length = 32 +1
                    sp = sp[ul:]
                    sn = '     '
                    if usr+1 >= 10: sn = '    '
                    if usr+1 >= 100: sn = '   '
                    if usr+1 >= 1000: sn = '  '
                    if user.id == topScore[usr][0]:
                        msg = msg+"#({}){}| » {} |  ({})\n".format(usr+1, sn, topScore[usr][2]+sp, topScore[usr][1])
                        userFound = True
                        userFoundPage = totalPages
                    else:
                        msg = msg+"#({}){}|   {} |  ({})\n".format(usr+1, sn, topScore[usr][2]+sp, topScore[usr][1])
                    usr += 1
                pages.append(msg)
                totalPages += 1
                msg = ""
                usr += 1
            # Determine what page to show.
            if page <= -1:# Show page with user.
                selectPage = userFoundPage
            elif page >= totalPages:
                selectPage = totalPages-1# Flood -1
            elif page in range(0, totalPages):
                selectPage = page
            else:# Show page 0
                selectPage = 0
            await self.bot.say( "{}{}\nTotal players:({})\nPage:({}/{})```".format(msgHeader, pages[selectPage], playerAmount, selectPage+1, totalPages))
        else:
            await self.bot.say( "`No accounts in the Four in a row register`".format(user.mention))
            logger.info("Error @ _leaderboard, players < 1")

    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Moderator Commands @ 4row
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    @_4row.command(name="stpg", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _stpg(self, ctx):
        """Force stop/delete a game from the channel.
        Admin/owner restricted."""
        user= ctx.message.author
        server = ctx.message.server
        await self.stop_game(ctx)
        logger.info("{}({}) has removed the Game from {}({})".format(user, user.id, ctx.message.channel, ctx.message.channel.id))
        await self.bot.say("{} ` Game stopped. `".format(user.mention))
        
    @_4row.command(name="maxplayers", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _maxplayers(self, ctx, maxp: int):
        """Changes the maximum amount of players that can join a game.
        Admin/owner restricted."""
        user= ctx.message.author
        if maxp <= 4:
            self.settings["MAX_PLAYERS"] = maxp
            await self.bot.say("{} ` The maximum amount of players in game is now {}. `".format(user.mention, str(maxp)))
            logger.info("{}({}) has set MAX_PLAYERS = {}".format(user, user.id, str(maxp)))
            fileIO(SETTINGS, "save", self.settings)
        else:
            await self.bot.say("{} ` Game is limited to 4 players max. `".format(user.mention))

    @_4row.command(name="expiretime", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _expiretime(self, ctx, expireTime : int):
        """Changes the expire time for a game.
        Admin/owner restricted."""
        user= ctx.message.author
        if expireTime == 0:
            expireTime = 1
        self.settings["EXPIRE_TIME"] = expireTime
        await self.bot.say("{} ` Game expires after {} seconds.`".format(user.mention, str(expireTime)))
        logger.info("{}({}) has set EXPIRE_TIME = {}".format(user, user.id, str(expireTime)))
        fileIO(SETTINGS, "save", self.settings)

    @_4row.command(name="unlocktime", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _unlocktime(self, ctx, unlockTime : int):
        """Changes the time to unlock voting.
        Admin/owner restricted."""
        user= ctx.message.author
        if unlockTime == 0:
            unlockTime = 1
        self.settings["VOTE_UNLOCK_TIME"] = unlockTime
        await self.bot.say("{} ` Game voting unlocks at {} seconds.`".format(user.mention, str(unlockTime)))
        logger.info("{}({}) has set VOTE_UNLOCK_TIME = {}".format(user, user.id, str(unlockTime)))
        fileIO(SETTINGS, "save", self.settings)

    @_4row.command(name="unlockvotes", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _unlockvotes(self, ctx, minVotes : int):
        """Changes the amount of votes to unlock a game for stop.
        Admin/owner restricted."""
        user= ctx.message.author
        self.settings["MIN_VOTES_TO_UNLOCK"] = minVotes
        await self.bot.say("{} ` Game now stops after {} votes.`".format(user.mention, str(minVotes)))
        logger.info("{}({}) has set MIN_VOTES_TO_UNLOCK = {}".format(user, user.id, str(minVotes)))              
        fileIO(SETTINGS, "save", self.settings)

    @_4row.command(name="togglebot", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _togglebot(self, ctx):
        """Enable/Disables the use of a bot player *you should leave this disabled for now.
        Admin/owner restricted."""
        user= ctx.message.author
        if self.settings["BOT_SETTINGS"]["ENABLED"]:
            self.settings["BOT_SETTINGS"]["ENABLED"] = False
            allowBot = "Disabled"
        elif not self.settings["BOT_SETTINGS"]["ENABLED"]:
            self.settings["BOT_SETTINGS"]["ENABLED"] = True
            allowBot = "Enabled"
            await self.bot.say("`Work in progress. Be aware that enabling and using this may cause strange behaviour`")#deleteme
        await self.bot.say("{} ` The in-game bot is now: {}.`".format(user.mention, allowBot))
        logger.info("{}({}) has {} the in-game bot.".format(user, user.id, allowBot.upper()))
        fileIO(SETTINGS, "save", self.settings)

    @_4row.command(name="toggleqmsg", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _toggleqmsg(self, ctx):
        """Enable/Disables player comments.
        Admin/owner restricted."""
        user= ctx.message.author
        if self.settings["ENA_QUEUE_MSG"]:
            self.settings["ENA_QUEUE_MSG"] = False
            allowMsg = "Disabled"
        elif not self.settings["ENA_QUEUE_MSG"]:
            self.settings["ENA_QUEUE_MSG"] = True
            allowMsg = "Enabled"
        await self.bot.say("{} ` The in-game user comments are now: {}.`".format(user.mention, allowMsg))
        logger.info("{}({}) has {} the in-game user comments.".format(user, user.id, allowMsg.upper()))     
        fileIO(SETTINGS, "save", self.settings)

    @_4row.command(name="botdifficulty", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _botdifficulty(self, ctx, difficulty : str):
        """Changes the default l33tnes of the bot.
        Admin/owner restricted."""
        user= ctx.message.author
        if difficulty in self.settings["BOT_SETTINGS"]["DIFFICULTY"]:
            if difficulty == "EASY":
                difficultySet = self.settings["BOT_SETTINGS"]["DIFFICULTY"]["EASY"]
            elif difficulty == "NOVICE":
                difficultySet = self.settings["BOT_SETTINGS"]["DIFFICULTY"]["NOVICE"]
            elif difficulty == "HARD":
                difficultySet = self.settings["BOT_SETTINGS"]["DIFFICULTY"]["HARD"]
            self.settings["BOT_SETTINGS"]["DEFAULT_DIFFICULTY"] = difficultySet
            await self.bot.say("{} ` Game bot difficulty is now {}.`".format(user.mention, difficulty))
            logger.info("{}({}) has set DEFAULT_DIFFICULTY = {}".format(user, user.id, str(difficulty)))
            fileIO(SETTINGS, "save", self.settings)
        else:
            await self.bot.say("{} ` Choose between EASY, NOVICE , HARD.`")
        fileIO(SETTINGS, "save", self.settings)

    @_4row.command(name="backup", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _backup(self, ctx):
        """Backup a copy of the user database.
        Admin/owner restricted."""
        user= ctx.message.author
        if not fileIO(BACKUP, "check"):
            logger.info("Writing a Backup ...")
            fileIO(BACKUP, "save", self.players)
            await self.bot.say("{} ` Backup done.`".format(user.mention, BACKUP))
            logger.info("{}({}) has made a BACKUP ({})".format(user, user.id, BACKUP))
        elif fileIO(BACKUP, "check"):
            await self.bot.say("` Backup found, overwrite it? yes/no`")
            response = await self.bot.wait_for_message(author=ctx.message.author)
            if response.content.lower().strip() == "yes":
                logger.info("Overwriting Backup")
                fileIO(BACKUP, "save", self.players)
                await self.bot.say("{} ` Backup done.`".format(user.mention))
                logger.info("{}({}) has made a BACKUP ({})".format(user, user.id, BACKUP))
            else:
                await self.bot.say("`Backup cancled.`")

    @_4row.command(name="restore", pass_context=True)
    @checks.admin_or_permissions(manage_server=True)
    async def _restore(self, ctx):
        """Restore a copy of the user database.
        Admin/owner restricted."""
        user= ctx.message.author
        if not fileIO(BACKUP, "check"):
            logger.info("No backup Found!")
            await self.bot.say("{} ` No backup Found!`".format(user.mention))
            logger.info("{}({}) Restoring backup FAILED ({})".format(user, user.id, BACKUP))
        elif fileIO(BACKUP, "check"):
            if fileIO(PLAYERS, "check"):
                await self.bot.say("` a players.json is found, overwrite it with the backup data? yes/no`")
                response = await self.bot.wait_for_message(author=ctx.message.author)
                if response.content.lower().strip() == "yes":
                    logger.info("Restoring players.json ...")
                    backup = fileIO(BACKUP, "load")
                    fileIO(PLAYERS, "save", backup)
                    await self.bot.say("{} ` Backup restored.`".format(user.mention))
                    logger.info("{}({}) Has RESTORED the backup ({})".format(user, user.id, BACKUP))
                else:
                    await self.bot.say("` Restore cancled.`")
            else:
                logger.info("Restoring players.json ...")
                backup = fileIO(BACKUP, "load")
                fileIO(PLAYERS, "save", backup)
                await self.bot.say("{} ` Backup restored.`".format(user.mention))
                logger.info("{}({}) Has RESTORED the backup ({})".format(user, user.id, BACKUP))        

    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Various Functions
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

     # Check if there is an account made.
    def account_check(self, id):
        try:
            REG_PLAYERS = self.players["PLAYERS"]
            data = True
        except:
            data = False
        if data:
            if id in REG_PLAYERS:
                return True
            else:
                return False
        else:
            return False

    # Check if user.id is currently in channel.id game.
    def ingame_check(self, ctx, userId):
        try:
            activePlayers = self.game["CHANNELS"][ctx.message.channel.id]["activePlayers"]
            data = True
        except:
            data = False
        if data:
            for usr in range(activePlayers):
                if userId == self.game["CHANNELS"][ctx.message.channel.id]["PLAYERS"]["IDS"][usr]:
                    return True
            return False
        else:
            return False

    # Generate an empty board.  
    def empty_board(self, size):
        board = []
        for x in range(self.settings["BOARDHEIGHT"][size]):
            board.append([self.EMPTY] * self.settings["BOARDWIDTH"][size])
        return board

    # Register a player.
    async def register_player(self, ctx, user):
        if user == ctx.message.server.me:
            preferred = self.settings["BOT_SETTINGS"]["TOKEN"]
            print(preferred)
            playerMsg = "nomsg"
            joiningMsg = "Initializing cheats..."
            victoryMsg = "Next..."
        else:
            preferred = 0
            playerMsg = "nomsg"
            joiningMsg = "Newbie"
            victoryMsg = "nomsg"
        self.players["PLAYERS"][user.id] = {"boardId": "noGame", 
                                                            "tokenPreferred": preferred, 
                                                            "tokenAssinged": 0, 
                                                            "playerId": user.id, 
                                                            "playerName": user.name, 
                                                            "MSG": {"playerMsg": playerMsg, "victoryMsg": victoryMsg, "joiningMsg": joiningMsg}, 
                                                            "STATS": {"won": 0, "loss": 0, "draw": 0, "wasted": 0, "totalMoves": 0, "points" : 10,"averageTimeTurn": 0, "avarageTimeGame": 0}}
        fileIO(PLAYERS, "save", self.players)
        if user == ctx.message.server.me:
            logger.info("Four in a row bot account created by channel: {}".format(ctx.message.channel.id))
        else:
            msg = ("{} `Account created`".format(user.mention))
            return {"showMsg": True, "msg": msg}

    # Join Game.
    async def join_game(self, ctx, user):
        msg = ""
        CH_PLAYERS = self.game["CHANNELS"][ctx.message.channel.id]["PLAYERS"]
        if user.id not in self.players["PLAYERS"]:
            msg = ("{} ` You need to be registered to join or start a game.\nType: '{}4row register'`".format(user.mention, self.PREFIXES[0]))
            return {"delMsg": False, "showMsg": True, "drawBoard": False, "msg": msg}
        elif user.id in self.players["PLAYERS"]:
            if ctx.message.channel.id in self.game["CHANNELS"]:
                activePlayers = self.game["CHANNELS"][ctx.message.channel.id]["activePlayers"]
                if activePlayers >= 0 and activePlayers <= self.settings["MAX_PLAYERS"]-1: # At least one free slot.
                    # Check if user is already in game.
                    if user.id in CH_PLAYERS["IDS"]:
                        msg = ("{} `You already joined...`".format(user.mention))
                        return {"delMsg": False, "showMsg": True, "drawBoard": False, "msg": msg}
                    elif user.id not in CH_PLAYERS["IDS"]:
                        # Add user to game.
                        CH_PLAYERS["NAMES"].append(user.name)
                        CH_PLAYERS["IDS"].append(user.id)
                        CH_PLAYERS["TOKENS"].append(0)
                        self.game["CHANNELS"][ctx.message.channel.id]["turnIds"].append(user.id)
                        self.players["PLAYERS"][user.id]["playerName"] = user.name
                        if user.id != ctx.message.server.me: # Escape bot.
                           self.players["PLAYERS"][user.id]["MSG"]["playerMsg"] = "nomsg"
                        self.game["CHANNELS"][ctx.message.channel.id]["PLAYERS"] = CH_PLAYERS
                        fileIO(GAMES, "save", self.game)
                        # User is now a part of total players.
                        activePlayers += 1
                        self.game["CHANNELS"][ctx.message.channel.id]["activePlayers"] = activePlayers
                        # Attach game to user.
                        self.players["PLAYERS"][user.id]["boardId"] = ctx.message.channel.id
                        # Assign token (switch from none/:x: to preferred OR available).
                        msg = await self.token_switch(ctx, user)
                        # Scale Board.
                        if activePlayers <= 2:#2
                            self.game["CHANNELS"][ctx.message.channel.id]["boardSize"] = 0
                            self.game["CHANNELS"][ctx.message.channel.id]["board"] = self.empty_board(0)
                        elif activePlayers == 3:#3
                            self.game["CHANNELS"][ctx.message.channel.id]["boardSize"] = 1
                            self.game["CHANNELS"][ctx.message.channel.id]["board"] = self.empty_board(1)
                        elif activePlayers == 4:#4
                            self.game["CHANNELS"][ctx.message.channel.id]["boardSize"] = 2
                            self.game["CHANNELS"][ctx.message.channel.id]["board"] = self.empty_board(2)
                        else:
                            self.game["CHANNELS"][ctx.message.channel.id]["boardSize"] = 0
                            self.game["CHANNELS"][ctx.message.channel.id]["board"] = self.empty_board(0)
                        await self.reset_voting(ctx)
                        # Save it all.
                        fileIO(GAMES, "save", self.game)
                        fileIO(PLAYERS, "save", self.players)
                        # Output msg.
                        if activePlayers <= 1:
                            msg = ("\n` I need at least one more player. \nType: '{}4row join' to join this game...`\n{}".format(self.PREFIXES[0], msg))
                            return {"delMsg": True, "showMsg": True, "drawBoard": True, "msg": msg}
                        elif activePlayers >= 2:
                            msg = ("\n` Type '{}4row start' to play`{}".format(self.PREFIXES[0], msg))
                            return {"delMsg": True, "showMsg": True, "drawBoard": True, "msg": msg}
                elif activePlayers >= self.settings["MAX_PLAYERS"]:
                    msg = ("{} ` Sorry no slots available, try again next game.`".format(user.mention))
                    return {"delMsg": False, "showMsg": True, "drawBoard": False, "msg": msg}
            else:
                msg = ("{} ` No game pending, type '{}4row new' to start one.`".format(user.mention, self.PREFIXES[0]))
                return {"delMsg": False, "showMsg": True, "drawBoard": False, "msg": msg}
        else:
            return {"delMsg": True, "showMsg": True, "drawBoard": True, "msg": msg}

    # Leave the game.
    async def leave_game(self, ctx, user):
        try:
            activePlayers = self.game["CHANNELS"][ctx.message.channel.id]["activePlayers"]
            inQue = self.game["CHANNELS"][ctx.message.channel.id]["inQue"]
            data = True
        except Exception as e:
            logger.info(e)
            data = False        
        if user == ctx.message.server.me:
            removeBot = True
        else:
            removeBot = False
        deleted = False
        for usr in range(0, activePlayers):
            if user.id == self.game["CHANNELS"][ctx.message.channel.id]["PLAYERS"]["IDS"][usr]:# Get user position.
                # turnIds and activePlayers are crucial for an started game.
                if self.game["CHANNELS"][ctx.message.channel.id]["inQue"] == "yes":
                    self.players["PLAYERS"][user.id]["boardId"] = "noGame"
                    self.players["PLAYERS"][user.id]["MSG"]["playerMsg"] = "has left"
                    # Delete user from game.
                    for usr2 in range(activePlayers): # usr2 == usr1 ?
                        if self.game["CHANNELS"][ctx.message.channel.id]["PLAYERS"]["IDS"][usr2] == user.id:
                            # Remove board id from user.
                            self.players["PLAYERS"][user.id]["boardId"] = "noGame"
                            self.players["PLAYERS"][user.id]["MSG"]["playerMsg"] = "has left"
                            # Delete user items from game.
                            del self.game["CHANNELS"][ctx.message.channel.id]["PLAYERS"]["IDS"][usr2]
                            del self.game["CHANNELS"][ctx.message.channel.id]["PLAYERS"]["NAMES"][usr2]
                            del self.game["CHANNELS"][ctx.message.channel.id]["PLAYERS"]["TOKENS"][usr2]
                            del self.game["CHANNELS"][ctx.message.channel.id]["turnIds"][usr2]
                            activePlayers -= 1
                            self.game["CHANNELS"][ctx.message.channel.id]["activePlayers"] = activePlayers
                            # Adjust "empty" board size.
                            if activePlayers <= 2:
                                self.game["CHANNELS"][ctx.message.channel.id]["boardSize"] = 0
                            elif activePlayers == 3:
                                self.game["CHANNELS"][ctx.message.channel.id]["boardSize"] = 1
                            elif activePlayers == 4:
                                self.game["CHANNELS"][ctx.message.channel.id]["boardSize"] = 2
                            else:
                                self.game["CHANNELS"][ctx.message.channel.id]["boardSize"] = 0
                            deleted = True
                            break
                elif self.game["CHANNELS"][ctx.message.channel.id]["inQue"] == "no":
                    # Set next turn before we skip id.
                    self.next_turn(ctx, user)# May need a check for turn, for now it seems to work ok.
                    # Remove board id from user.
                    self.players["PLAYERS"][user.id]["boardId"] = "noGame"
                    self.players["PLAYERS"][user.id]["MSG"]["playerMsg"] = "has left"
                    # Ad user id to skipIds.
                    self.game["CHANNELS"][ctx.message.channel.id]["skipIds"].append(user.id)
                    # Remove player from turnIds.
                    for usr3 in range(len(self.game["CHANNELS"][ctx.message.channel.id]["turnIds"])):
                        if self.game["CHANNELS"][ctx.message.channel.id]["turnIds"][usr3] == user.id:
                            del self.game["CHANNELS"][ctx.message.channel.id]["turnIds"][usr3]
                            deleted =True
                            break
                    break        
                break
        fileIO(PLAYERS, "save", self.players)
        fileIO(GAMES, "save", self.game)
        inGameIds = len(self.game["CHANNELS"][ctx.message.channel.id]["turnIds"])
        # Check amount of users in still in-game.
        stopGame = False
        if inGameIds < self.settings["MIN_PLAYERS"] and inQue == "no":
            stopGame = True
        else:
            stopGame = False            
        # When one player left in active game.
        if deleted and stopGame and inQue == "no": 
           #await self.stop_game(ctx)
           msg = ("\n{} `I've removed you from the game. Well done {}, you ruined the game...`".format(user.mention, user))
           return {"delMsg": False, "showMsg": True, "drawBoard": True, "msg": msg, "stopGame": True}
        # When game in queue.
        elif deleted and not stopGame:
            msg = ("\n{} ` has left the game.`".format(user.mention))
            return {"delMsg": True, "showMsg": True, "drawBoard": True, "msg": msg, "stopGame": False}
        # This shouldn't happen.
        else:
            logger.info("Error at leave_game.\n  id:{}, MIN_PLAYERS{}, stopGame:{} ".format(user.id, self.settings["MIN_PLAYERS"], str(stopGame)))
            await self.dump_data()
            msg = ("\n{} ` Unknown error.`".format(user.mention))
            return {"delMsg": True, "showMsg": True, "drawBoard": False, "msg": msg, "stopGame": False}

    # Start the game.
    async def start_game(self, ctx, userId):
        self.game["CHANNELS"][ctx.message.channel.id]["inQue"] = 'no'
        await self.reset_voting(ctx)
        self.stats["gamesStarted"] += 1
        fileIO(STATS, "save", self.stats)         
        fileIO(GAMES, "save", self.game)

    # Stop the game.
    async def stop_game(self, ctx):
        # Remove boardId from joined users of the game.
        try:
            for usr in range(len(self.game["CHANNELS"][ctx.message.channel.id]["PLAYERS"]["IDS"])):
                self.players["PLAYERS"][self.game["CHANNELS"][ctx.message.channel.id]["PLAYERS"]["IDS"][usr]]["boardId"] = "noGame"
        except Exception as e:
            logger.info(e)
            logger.info("Error deleting {} from users. It seems that the game with user ids is already deleted elsewhere, check code and JSON)".format(ctx.message.channel.id))
            await self.dump_data()
        # Remove channel from games.
        try:
            del self.game["CHANNELS"][ctx.message.channel.id]
            self.stats["gamesStopped"] += 1
            fileIO(STATS, "save", self.stats)
        except Exception as e:
            logger.info(e)
            logger.info("Error deleting {} from games. It seems that this game is already deleted elsewhere, check code and JSON)".format(ctx.message.channel.id))
            await self.dump_data()
        fileIO(GAMES, "save", self.game)
        fileIO(PLAYERS, "save", self.players)

    # Reset/update these after changes.
    async def reset_voting(self, ctx):
        now = round(time.time())
        self.game["CHANNELS"][ctx.message.channel.id]["lastActivity"] =  now 
        self.game["CHANNELS"][ctx.message.channel.id]["VOTES_STP"]["votes"] = 0
        self.game["CHANNELS"][ctx.message.channel.id]["VOTES_STP"]["voteIds"] = []
        fileIO(GAMES, "save", self.game)

    # Returns avaiable tokens in message format.
    async def msg_available_tokens(self):
        tokens = deepcopy(self.TOKENS)
        tokens.pop(0)
        done = 0
        lenLang = len(tokens)
        msg = ""
        while (done < lenLang):
            w=done+4
            while (w > done and done < lenLang):
                msg = msg + "{} = {}, ".format(str(done+1), tokens[done][1])
                done += 1
            msg = msg + "\n"
        done += 1
        if len(msg) > 10:
            msg = "\nAvailable Tokens for Four in a row:\n\n{}\n".format(msg)
        return msg

    # Returns an number array of unused tokens.
    async def token_switch(self, ctx, user="", newToken=0):
        msg = "\n`Error token switch`"
        if user == "":
            logger.info("Error token_switch, check script for 'user'.\n ctx: {}, newToken: {}'".format(ctx, newToken))
            return msg
        usedTokens = []
        availableTokens = []
        playersInQue = []
        # Check if user has joined the channel game.
        if self.players["PLAYERS"][user.id]["boardId"] is ctx.message.channel.id:
            # Assign with newToken >= 1 (!mytoken) OR load with newToken = 0 (join game)
            if newToken == 0:
                newToken = self.players["PLAYERS"][user.id]["tokenPreferred"]
            try:
                inQue = self.game["CHANNELS"][ctx.message.channel.id]["inQue"]
                CH_PLAYERS = self.game["CHANNELS"][ctx.message.channel.id]["PLAYERS"]
                usedTokens = CH_PLAYERS["TOKENS"]
                playersInQue = CH_PLAYERS["IDS"]
                data = True
            except Exception as e:
                logger.info(e)
                data = False
            # Preferred has no special conditions.
            self.players["PLAYERS"][user.id]["tokenPreferred"] = newToken
            if data and inQue == "yes":
                # Filter usable values from TOKENS.
                for (key, t) in enumerate(self.TOKENS):
                    availableTokens.append(key)
                unusedTokens = self.get_unused(availableTokens, usedTokens)
                # Get user index position in game.
                userPos = -1
                if len(CH_PLAYERS["IDS"]) >= 0:
                    for usr in range(len(CH_PLAYERS["IDS"])):
                        if CH_PLAYERS["IDS"][usr] == user.id:
                            userPos = usr
                            break
                if newToken not in usedTokens:
                    # Set preferred token in game.
                    CH_PLAYERS["TOKENS"][userPos] = newToken
                    self.players["PLAYERS"][user.id]["tokenAssinged"] = newToken
                    #print("token assigned {}".format(newToken))
                    msg = ""
                    #msg = ( "{} \n`Your preferred and assigned token is: {}\n `{}"
                    #           .format(user.mention, self.TOKENS[newToken][0], self.TOKENS[newToken][1]))
                else:
                    # Set random token in game.
                    newToken = random.choice(unusedTokens)
                    CH_PLAYERS["TOKENS"][userPos] = newToken
                    
                    self.players["PLAYERS"][user.id]["tokenAssinged"] = newToken
                    msg = ( "\n\n{}`Your preferred token is set, but already used in the current game or default...\nSo I've randomly assiged you: {}`{}\n`Type {}help 4row for more info\n `"
                                .format(user.mention, self.TOKENS[newToken][0], self.TOKENS[newToken][1], self.PREFIXES[0]))
            elif inQue == "no":
                # Set preferred token in players.
                self.players["PLAYERS"][user.id]["tokenPreferred"] = newToken
                msg = ("\n\n{}`Your preferred token is: {}` {}\n`Since you are in game, it wil be available next game`"
                            .format(user.mention, self.TOKENS[newToken][0], self.TOKENS[newToken][1]))
            # Save it all.
            fileIO(PLAYERS, "save", self.players)
            fileIO(GAMES, "save", self.game)
            return msg
        else: # Not in game.
            # Set preferred token in players.
            self.players["PLAYERS"][user.id]["tokenPreferred"] = newToken
            msg = ( "\n`Your preferred token is: {}\n ` {}"
                        .format(self.TOKENS[newToken][0], self.TOKENS[newToken][1]))
            fileIO(PLAYERS, "save", self.players)
            return msg

    # Check id is turn.
    async def my_turn(self, ctx, userId):
        turn = self.game["CHANNELS"][ctx.message.channel.id]["turnIds"][0]
        if userId == turn:
            return True
        elif userId != turn:   
            return False
        else:
            logger.info("Error my_turn.\n ctx: {} userId: {}".format(ctx, userId))
            await self.dump_data()
            return False

    # Check if there are no empty spaces anywhere on the board.
    def board_full(self, ctx):
        board = self.game["CHANNELS"][ctx.message.channel.id]["board"]
        BOARD_SIZE = self.game["CHANNELS"][ctx.message.channel.id]["boardSize"]
        for x in range(self.settings["BOARDHEIGHT"][BOARD_SIZE]):
            for y in range(self.settings["BOARDWIDTH"][BOARD_SIZE]):
                if board[x][y] == self.EMPTY:
                    return False
        return True

    # Return the row number of the lowest empty row in the given column.
    def lowest_empty_space(self, ctx, column):
        board = self.game["CHANNELS"][ctx.message.channel.id]["board"] 
        BOARD_SIZE = self.game["CHANNELS"][ctx.message.channel.id]["boardSize"]
        for y in range(self.settings["BOARDHEIGHT"][BOARD_SIZE]-1, -1, -1):
            if board[y][column] == self.EMPTY:
                return y
            else:
                pass
        return -1

    # Make a move and set next turn.
    async def make_move(self, ctx, user, column, freePos):
        userToken = self.TOKENS[0][0] # Tracing
        CH_GAME = self.game["CHANNELS"][ctx.message.channel.id]
        CH_PLAYERS = CH_GAME["PLAYERS"]
        BOARD_SIZE = CH_GAME["boardSize"]
        BOARDHEIGHT = self.settings["BOARDHEIGHT"][BOARD_SIZE]        
        stringgame = CH_GAME["board"]
        activePlayers = CH_GAME["activePlayers"]
        # Set time it took to make a move, and update the number of moves.
        self.players["PLAYERS"][user.id]["STATS"]["totalMoves"] += 1
        totalMoves = self.players["PLAYERS"][user.id]["STATS"]["totalMoves"]
        now = round(time.time())
        turnTime = (now - CH_GAME["lastActivity"])/totalMoves
        self.players["PLAYERS"][user.id]["STATS"]["averageTimeTurn"] = turnTime
        fileIO(PLAYERS, "save", self.players)
        # Get position of user.
        userPos = -1
        if activePlayers >= 1:
            for usr in range(activePlayers):
                if CH_PLAYERS["IDS"][usr] == user.id:
                    userPos = usr
                    break
        userToken = self.TOKENS[CH_PLAYERS["TOKENS"][userPos]][0]
        # Add token to board at given column.
        for y in range(BOARDHEIGHT-1, -1, -1):
            if y == freePos:# When indexing reaches free position.
                self.game["CHANNELS"][ctx.message.channel.id]["board"][y][column] = userToken         
        self.next_turn(ctx, user)
        await self.reset_voting(ctx)
        # Save it.
        self.game["CHANNELS"][ctx.message.channel.id]["PLAYERS"] = CH_PLAYERS
        fileIO(GAMES, "save", self.game)

    # Returns an unused index of an araay.
    def get_unused(self, arrayAvailable, arrayUsed):
        output = []
        seen = set()
        for value in arrayAvailable:
            if value not in arrayUsed and value not in seen:
                output.append(value)
                seen.add(value)
        return output

    # Set next turn (array order).
    def next_turn(self, ctx, user):
        CH_GAME = self.game["CHANNELS"][ctx.message.channel.id]
        CH_PLAYERS = CH_GAME["PLAYERS"]
        skipIds = CH_GAME["skipIds"]
        turnIds = CH_GAME["turnIds"]
        activePlayers = CH_GAME["activePlayers"]
        nextTurn = 'ERRnt' # Trace.
        userPos = -1
        if activePlayers >= 1:
            for usr in range(activePlayers):
                if CH_PLAYERS["IDS"][usr] == user.id:
                    userPos = usr
                    break
        if turnIds[0] == CH_PLAYERS["IDS"][userPos]:
            nextTurn = self.shift(turnIds, -1)# Shift id.
            # Check if player has left the game.
            if nextTurn[0] in skipIds:
                nextTurn = self.shift(turnIds, -1)# Skip id.
            self.game["CHANNELS"][ctx.message.channel.id]["turnIds"] = nextTurn
        # Save all
        self.game["CHANNELS"][ctx.message.channel.id]["PLAYERS"] = CH_PLAYERS
        fileIO(GAMES, "save", self.game)        

    # Check if a certain token makes a winner.
    def is_winner(self, ctx, tile):
        board = self.game["CHANNELS"][ctx.message.channel.id]["board"]
        BOARD_SIZE = self.game["CHANNELS"][ctx.message.channel.id]["boardSize"]
        BOARDHEIGHT = self.settings["BOARDHEIGHT"][BOARD_SIZE]   
        BOARDWIDTH = self.settings["BOARDWIDTH"][BOARD_SIZE]   

        # Check horizontal.
        for x in range(BOARDHEIGHT - 3):
            for y in range(BOARDWIDTH):
                if board[x][y] == tile and board[x+1][y] == tile and board[x+2][y] == tile and board[x+3][y] == tile:
                    return True
        # Check vertical.
        for x in range(BOARDHEIGHT):
            for y in range(BOARDWIDTH - 3):
                if board[x][y] == tile and board[x][y+1] == tile and board[x][y+2] == tile and board[x][y+3] == tile:
                    return True
        # Check / diagonal.
        for x in range(BOARDHEIGHT - 3):
            for y in range(3, BOARDWIDTH):
                if board[x][y] == tile and board[x+1][y-1] == tile and board[x+2][y-2] == tile and board[x+3][y-3] == tile:
                    return True
        # Check \ diagonal.
        for x in range(BOARDHEIGHT - 3):
            for y in range(BOARDWIDTH - 3):
                if board[x][y] == tile and board[x+1][y+1] == tile and board[x+2][y+2] == tile and board[x+3][y+3] == tile:
                    return True
        return False

    # Retuns a list of top scores.
    async def get_rankings(self, ctx, userId=None):
        user = ctx.message.author
        # Get all earned points of players.
        topScore = []
        if len(self.players["PLAYERS"]) >= 1:
            for p in self.players["PLAYERS"]:
                points = self.players["PLAYERS"][p]["STATS"]["points"]
                userName = self.players["PLAYERS"][p]["playerName"]
                topScore.append((p, points, userName))            
            topScore = sorted(topScore, key=itemgetter(1), reverse=True)
        # Get player rank.
        userIdRank = 0
        for index, p in enumerate(topScore):
            if p[0] == user.id:
                userIdRank = index+1
                break
        return {"topScore": topScore, "userIdRank": userIdRank}

    # Update statistics of ingame players.
    async def update_score(self, ctx):  
        try:
            CH_GAME = self.game["CHANNELS"][ctx.message.channel.id]
            CH_PLAYERS = CH_GAME["PLAYERS"]
            winnerId = CH_GAME["winner"]
        except Exception as e:
            logger.info(e)
            logger.info("Error getting IDS @ update_score, check code and json dump.")
            await self.dump_data()
            return
        user = ctx.message.author
        now = round(time.time())
        gameDuration = now-CH_GAME["gameStarted"]
        # Set score to all players in game.
        for usr in range(0, len(CH_PLAYERS["IDS"])):
            userId = CH_PLAYERS["IDS"][usr]
            if winnerId == "draw":# Draw.
                stats = self.players["PLAYERS"][userId]["STATS"]
                self.players["PLAYERS"][userId]["STATS"]["draw"] += 1
                self.players["PLAYERS"][userId]["STATS"]["points"] += self.settings["REWARDS"]["DRAW"]
                userTotalGames = stats["won"]+stats["loss"]+stats["draw"]+stats["wasted"]
                avarageTimeGame = (stats["avarageTimeGame"] + gameDuration)/userTotalGames
                self.players["PLAYERS"][userId]["STATS"]["avarageTimeGame"] += avarageTimeGame
                msg = self.get_queue_msg(stats)
                self.players["PLAYERS"][userId]["MSG"]["joiningMsg"] = msg
                continue# Skip next checks.
            elif winnerId == userId:# Winner.
                stats = self.players["PLAYERS"][userId]["STATS"]
                self.players["PLAYERS"][userId]["STATS"]["won"] += 1
                self.players["PLAYERS"][userId]["STATS"]["points"] += self.settings["REWARDS"]["WINNING"]
                userTotalGames = stats["won"]+stats["loss"]+stats["draw"]+stats["wasted"]
                avarageTimeGame = (stats["avarageTimeGame"] + gameDuration)/userTotalGames
                self.players["PLAYERS"][userId]["STATS"]["avarageTimeGame"] += avarageTimeGame
                msg = self.get_queue_msg(stats)             
                self.players["PLAYERS"][userId]["MSG"]["joiningMsg"] = msg
                continue
            elif winnerId != userId:# Must be one of the losers.
                stats = self.players["PLAYERS"][userId]["STATS"]            
                self.players["PLAYERS"][userId]["STATS"]["loss"] += 1
                self.players["PLAYERS"][userId]["STATS"]["points"] += self.settings["REWARDS"]["LOSING"]
                userTotalGames = stats["won"]+stats["loss"]+stats["draw"]+stats["wasted"]
                avarageTimeGame = (stats["avarageTimeGame"] + gameDuration)/userTotalGames
                self.players["PLAYERS"][userId]["STATS"]["avarageTimeGame"] += avarageTimeGame
                msg = self.get_queue_msg(stats)
                self.players["PLAYERS"][userId]["MSG"]["joiningMsg"] = msg
                continue
        fileIO(PLAYERS, "save", self.players)
        return

    # Get the queue message / Rank.
    def get_queue_msg(self, stats):
        qMsgTrig = deepcopy(self.settings["TRIG_QUEUE_MSG"])
        msg = "hoax"# This should not reach the json.
        ponts = stats["points"]
        won = stats["won"]+stats["draw"]
        lost = stats["loss"]+stats["wasted"]
        total = won+lost
        if total == 0:
            total = 1# Ensure a safe calc.
        ratio = float(won)/(total)
        # Newbie.
        if total <= qMsgTrig[1][1]:
            msg = qMsgTrig[1][0]
        # No Newbie anymore.                
        elif total > qMsgTrig[1][1]:
            #Remove unwanted from list.     
            del qMsgTrig[0] # Minumum
            del qMsgTrig[0] # Newbie
            lenList = len(qMsgTrig) # lenList is absolute max. (flood for loop.)
            msg = qMsgTrig[0][0] # Player is at least a n00b.
            for m in range(0, lenList):
                # A player need the minumium ratio+total games to step up.
                if ratio >= qMsgTrig[m][2] and total >= qMsgTrig[m][1]:
                    msg = qMsgTrig[m][0] # Set lvl value as msg.
                    if ratio >= qMsgTrig[m+1][2] and total >= qMsgTrig[m+1][1]:
                        # Ratio+total games apears to be higher than next [m] value so lvl up.
                        msg = qMsgTrig[m+1][0]
                    else:
                        # Player will not step up, for loop ends here, status text from [m] is the amount of loops made.
                        msg = qMsgTrig[m][0]
                        break # No need to check any further.
                if m >= lenList-1:
                    break # Prevent indexError.
        return msg

    # Draw the board to chat.
    async def draw_board(self, ctx, comment, DM=False):
        user = ctx.message.author
        try: # Get exitsing game data.
            CH_GAME = self.game["CHANNELS"][ctx.message.channel.id]
            board = CH_GAME["board"]
            BOARD_SIZE = CH_GAME["boardSize"]
            turn = CH_GAME["turnIds"]
            inQue = CH_GAME["inQue"]
            CH_PLAYERS = CH_GAME["PLAYERS"]
            skipIds = CH_GAME["skipIds"]
            activePlayers = CH_GAME["activePlayers"]
            data = True
        except: # An empty board.
            board = self.empty_board(0)
            BOARD_SIZE = 0
            turn = ["none"]
            inQue = "yes"
            CH_PLAYERS = {"IDS": [], "NAMES": [], "TOKENS": []}
            skipIds = ["none"]
            comment = "\n` There you have it, an empty 'Four in a row' board.\nTo create a new game type: '{}4row new'`".format(self.PREFIXES[0])
            activePlayers = 0
            data = False
        userComment = "nomsg"
        slots = {"IDS": [], "NAMES": [], "TOKENS": [], "MSG": []}
        for slot in range(self.settings["MAX_PLAYERS"]):
            slots["IDS"].append("noId")
            slots["NAMES"].append("- EmptySlot #" + str(slot+1)+ " -")
            slots["TOKENS"].append(self.ICONS[1][1])  
            slots["MSG"].append(userComment)
        # Fill slot display up with players.
        if len(CH_PLAYERS["IDS"]) is not None:
            for usr in range(len(CH_PLAYERS["IDS"])):
                slots["IDS"][usr] = CH_PLAYERS["IDS"][usr]
                slots["NAMES"][usr] = CH_PLAYERS["NAMES"][usr]
                slots["TOKENS"][usr] = CH_PLAYERS["TOKENS"][usr]
                playerMsg = self.players["PLAYERS"][CH_PLAYERS["IDS"][usr]]["MSG"]["playerMsg"] 
                joiningMsg = self.players["PLAYERS"][CH_PLAYERS["IDS"][usr]]["MSG"]["joiningMsg"] 
                if CH_PLAYERS["IDS"][usr] in self.players["PLAYERS"] and playerMsg != "nomsg" or joiningMsg != "nomsg":
                    if self.settings["ENA_QUEUE_MSG"] and inQue == 'yes':
                        slots["MSG"][usr] = self.players["PLAYERS"][CH_PLAYERS["IDS"][usr]]["MSG"]["joiningMsg"]
                    elif self.settings["ENA_QUEUE_MSG"] and inQue == 'no':
                        slots["MSG"][usr] = self.players["PLAYERS"][CH_PLAYERS["IDS"][usr]]["MSG"]["playerMsg"]
                    else:
                        slots["MSG"][usr] = userComment                        
                else:
                    slots["MSG"][usr] = userComment     
        tokensWidth = []
        tokensHeight = []
        tokenDef = None
        msgBoard = '\n'
        # Build up a board, note: Display index of tokens != game index of tokens (x=y, y=x).
        for w in range(self.settings["BOARDWIDTH"][BOARD_SIZE]):
            msgBoard = msgBoard+emoji.emojize(self.BOARD_HEADER[w])
        msgBoard = msgBoard+'\n'
        for x in range(self.settings["BOARDHEIGHT"][BOARD_SIZE]):#6 = default
            for y in range(self.settings["BOARDWIDTH"][BOARD_SIZE]):#7 = default
                for z in range(len(self.TOKENS)):
                    if board[x][y] == self.TOKENS[z][0]:
                        tokenDef = emoji.emojize(self.TOKENS[z][1], use_aliases=True)# User Token.
                    elif board[x][y] == self.EMPTY:
                        tokenDef = emoji.emojize(self.ICONS[0][1], use_aliases=True)# Black.
                tokensWidth.append(tokenDef)
                msgBoard = (msgBoard+tokenDef)
            tokensHeight.append(tokensWidth)    
            msgBoard = (msgBoard+'\n')
        # Set-up user name/slot display.
        playerIs = ''
        if inQue == 'yes': # Draw slots.
            slotsLen = self.settings["MAX_PLAYERS"]
        elif inQue == 'no':# Game is started.
            slotsLen = activePlayers
        turnUserMsg = " "
        for usr in range(0, slotsLen):
            # Get player message.
            if slots["MSG"][usr] != "nomsg":
                if slots["IDS"][usr] == ctx.message.server.me.id:# Player is bot.
                    userComment = " ("+("Initialising Cheats...")+")"
                else:
                    userComment = " ("+str(slots["MSG"][usr])+")"
            else:
                userComment = ""
            # Get token/icon for slot.
            if slots["IDS"][usr] == "noId":
                tToken = emoji.emojize(' '+self.ICONS[1][1]) # Pointing arrow.
            else:
                tToken = emoji.emojize(self.TOKENS[CH_PLAYERS["TOKENS"][usr]][1])# Player token.
            # Game has started.
            if inQue == 'no' and turn[0] == slots["IDS"][usr] and slots["IDS"][usr] not in skipIds:
                mentionPlayer = turn[0]
                turnUserMsg = (slots["NAMES"][usr]+"'s turn:")
                # Highlight players.
                ul = len(slots["IDS"][usr])
                sp = '                                        «`'# Discord username max length = 32 +8
                sp = sp[ul:]
                playerIs = playerIs + ('  '+ tToken + '  ` ' + slots["NAMES"][usr] + sp + '\n') 
            # Game in Queue.
            else:
                if inQue == 'no' and slots["IDS"][usr] not in skipIds:
                    mentionPlayer = turn[0]# Should not be necessary.
                    playerIs = playerIs + ('  '+ tToken + '  ' + slots["NAMES"][usr] + '\n')
                elif inQue == 'no' and slots["IDS"][usr] in skipIds:
                    mentionPlayer = turn[0]
                    playerIs = playerIs + ('  '+ tToken + '  ' + '~~' + slots["NAMES"][usr]+'~~' + '\n')
                elif inQue == 'yes':
                    mentionPlayer = user.id
                    if not data:
                        turnUserMsg = "An unboxed game:"
                    elif data:
                        turnUserMsg = "Game in queue:"
                    playerIs = playerIs + ('  '+ tToken + '  ' + slots["NAMES"][usr] + userComment + '\n')
        # Output board.
        if DM:
            await self.bot.send_message(ctx.message.author, "{}\n{}\n**{}**\n{}{}\n\n".format('<@'+mentionPlayer+'>', msgBoard, turnUserMsg, playerIs, comment))
        elif not DM:
            await self.bot.send_message(ctx.message.channel, "{}\n{}\n**{}**\n{}{}\n\n".format('<@'+mentionPlayer+'>', msgBoard, turnUserMsg, playerIs, comment))

    # Shift an array.
    def shift(self, seq, n):
        shifted_seq = []
        for i in range(len(seq)):
            shifted_seq.append(seq[(i-n) % len(seq)])
        return shifted_seq

    # Dump data to json (from errors).
    async def dump_data(self):
        now = round(time.time())
        f = "{}\_datadump{}.json".format(DIR_DATA, str(now))
        s = "##############################################"
        jsons = [s, self.game, s, self.settings, s, self.players, s, self.stats, s]
        data = []
        for d in jsons:
            data.append(d)
        logger.info("Dumping data in: {}".format(f))
        fileIO(f, "save", data) 

    # Delete my message from chat.
    async def delete_message(self, ctx, number=1, delComm=False):
        server = ctx.message.server
        can_delete = ctx.message.channel.permissions_for(server.me).manage_messages
        user = ctx.message.server.me
        author = ctx.message.author
        message = ctx.message
        cmdmsg = message
        if number > 0 and number < 10000:
            while True:
                new = False
                async for x in self.bot.logs_from(ctx.message.channel, limit=100, before=message):
                    if number == 0:
                        if delComm and can_delete:
                            try:
                                await self.bot.delete_message(cmdmsg)
                            except Exception as e:
                                logger,info(e)
                                logger.info("I need more permissions @ {} to delete messages other than my own.".format(ctx.message.channel))
                        return         
                    if x.author.id == user.id:
                        await self.bot.delete_message(x)
                        number -= 1
                    new = True
                    message = x                        
                if not new or number == 0:
                    await self.bot.delete_message(cmdmsg)
                    break

    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Bot Player Specific Functions
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
       
    # The bot needs cheats.
    def bot_move(self, ctx):
        CH_GAME = self.game["CHANNELS"][ctx.message.channel.id]
        board = CH_GAME["board"] 
        BOARD_SIZE = CH_GAME["boardSize"]
        BOARDHEIGHT = self.settings["BOARDHEIGHT"][BOARD_SIZE]
        BOARDWIDTH = self.settings["BOARDWIDTH"][BOARD_SIZE]
        DIFFICULTY = CH_GAME["botDifficulty"]

        return

        botTokenAssigned = self.players["PLAYERS"][ctx.message.server.me.id]["tokenAssinged"]
        botToken = self.TOKENS[botTokenAssigned][0]
        potentialMoves = self.potential_moves(ctx, botToken, DIFFICULTY)
        print("potentialMoves")
        print(potentialMoves)
        # Get the best fitness from the potential moves.
        bestMoveFitness = -1
        for i in range(BOARDWIDTH):
            print(i)
            if potentialMoves[i] > bestMoveFitness and self.valididate_move(ctx, i):
                bestMoveFitness = potentialMoves[i]
        print("bestmovefitness:")
        print(bestMoveFitness)
        # Find all potential moves that have this best fitness.
        bestMoves = []
        for i in range(len(potentialMoves)):
            if potentialMoves[i] >= bestMoveFitness and self.valididate_move(ctx, i):
                bestMoves.append(i)
        print("bestmoves/random")
        print(bestMoves)
        if bestMoves != []:
            return random.choice(bestMoves)

    # Cheats (bot and admins only), figure out the best move to make.
    def potential_moves(self, ctx, tile, lookAhead):
        CH_GAME = self.game["CHANNELS"][ctx.message.channel.id]
        board = CH_GAME["board"]
        BOARD_SIZE = CH_GAME["boardSize"]
        BOARDHEIGHT = self.settings["BOARDHEIGHT"][BOARD_SIZE]
        BOARDWIDTH = self.settings["BOARDWIDTH"][BOARD_SIZE]
        enemyTokens = []

        potentialMoves = [0] * BOARDWIDTH

        if lookAhead == 0 or self.board_full(ctx):
            return [0] * BOARDWIDTH           
        for t in range(len(CH_GAME["PLAYERS"]["IDS"])):
            enemyTokens.append(self.TOKENS[CH_GAME["PLAYERS"]["TOKENS"][t]][0])
            enemys = t
        print("ensmys/enemy tokens")
        print(enemys)
        print(enemyTokens)
        # Two player test.
        # needs some kind of deep copy of ctx to check posibility's, or duplicate game functions to only check on a board.

        for firstMove in range(BOARDWIDTH):      
            if not self.valididate_move(ctx, firstMove):
                print("{} - not valid".format(firstMove))
                continue
            if self.is_winner(ctx, enemyTokens[0]):                
                potentialMoves[firstMove] = 1# Winning move gets a perfect fitness.
                print("{} - lowest_empty_space".format(firstMove))
                print(self.lowest_empty_space(ctx, firstMove))
                break# Don't bother calculating other moves.
            else:# No winning move, check another player.
                if self.board_full(ctx):
                    potentialMoves[firstMove] = 0         
                else:
                    print("Check enemy")
                    for counterMove in range(BOARDWIDTH): # Check counterMoves.
                        ctx2 = ctx#
                        if not self.valididate_move(ctx2, counterMove):
                            print("{} - not valid Enemy".format(counterMove))
                            continue
                        if self.is_winner(ctx2, enemyTokens[1]):
                            potentialMoves[counterMove] = 1# Winning enemy move gets a worst fitness.
                            print("{} - lowest_empty_space Enemy".format(counterMove))
                            print(self.lowest_empty_space(ctx2, counterMove))
                            break# Don't bother calculating other moves.
                        else:
                            # Make a recursive call to potential_moves()                        
                            results = self.potential_moves(ctx2, enemyTokens[1], lookAhead - 1)
                            print(results)
                            potentialMoves[firstMove] += (sum(results) / BOARDWIDTH) / BOARDWIDTH
        return potentialMoves

    # Validate move (bot), check if there is an empty space within the given column.
    def valididate_move(self, ctx, column):
        CH_GAME = self.game["CHANNELS"][ctx.message.channel.id]
        board = CH_GAME["board"]
        BOARD_SIZE = CH_GAME["boardSize"]
        BOARDHEIGHT = self.settings["BOARDHEIGHT"][BOARD_SIZE]
        BOARDWIDTH = self.settings["BOARDWIDTH"][BOARD_SIZE]
        if column < 0 or column > (BOARDHEIGHT) or board[column][0] != self.EMPTY:
            return False
        return True

    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
    # Development Commands
    #----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

    #Removed » https://github.com/Canule/marvin-DiscordBot/blob/develop/cogs/devt/devTool4row.py

#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
# Set-up
#-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

def check_folders():
    if not os.path.exists(DIR_DATA):
        print("Creating {} folder...".format(DIR_DATA))
        os.makedirs(DIR_DATA)

def check_files():
    # 1 player, 21dots
    # 2 players, 42dots = 7*6, Original game
    # 3 players, 63dots = 8*7,   8*7=56(-7)«    9*8=72(+9)
    # 4 players, 84dots = 10*9,  10*9=90(+6)«     9*8=72(-12)
    settings = {
                "BOARDWIDTH": [7, 8, 10], 
                "BOARDHEIGHT": [6, 7, 9], 
                "BOARD_HEADER": [":one:", ":two:", ":three:", ":four:", ":five:", ":six:", ":seven:", ":eight:", ":nine:", ":keycap_ten:", ":a:", ":b:", ":c:"], 
                "MIN_PLAYERS": 2, 
                "MAX_PLAYERS": 2, 
                "ENA_QUEUE_MSG": False, 
                "TRIG_QUEUE_MSG": [["", 0, 0.0, "x"], 
                                                ["a Newbie", 3, 0.0, "Newbie"], 
                                                ["a N00b", 5, 0.20, "*"], 
                                                ["An average player", 5, 0.4, "**"], 
                                                ["The Pro.", 10, 0.60, "****"], 
                                                ["The Unbeatable", 10, 1.0, "*****"],
                                                ["", sys.maxsize, 2.0]], 
                "MAX_LEN_USER_MSG": 30, 
                "REWARDS": {"WINNING": 40, "LOSING": 20, "DRAW": 50, "RUIENING": -15}, 
                "TIME_PENALTY": {"SLOW_MOVES_TIME": [60, 80, 120], "POINTS": [-3,-2,-1]}, 
                "EXPIRE_TIME": 900, 
                "VOTE_UNLOCK_TIME": 120, 
                "MIN_VOTES_TO_UNLOCK": 2, 
                "BOT_SETTINGS": {"ENABLED": False, "DEFAULT_DIFFICULTY": 1, "TOKEN": 3, "DIFFICULTY": {"EASY": 1 , "NOVICE": 2, "HARD": 4}}, 
                "ICONS": [["black", ":black_circle:"], ["arrow", "→"], ["recycle", ":recycle:"], ["cross", ":x:"]], 
                "TOKENS": [["none", ":x:"], ["red circle", ":red_circle:"], ["blue circle", ":large_blue_circle:"], ["baseball", ":baseball:"], ["tennisball", ":tennis:"], ["8ball", ":8ball:"], 
                                ["basketball", ":basketball:"], ["cd", ":cd:"], ["dvd", ":dvd:"], ["full moon", ":full_moon:"], ["new moon", ":new_moon:"], ["rice cracker", ":rice_cracker:"], 
                                ["no entry", ":no_entry:"], ["cherries", ":cherries:"], ["cookie", ":cookie:"], ["clover", ":four_leaf_clover:"], ["cyclone", ":cyclone:"], ["sunflower", ":sunflower:"], 
                                ["mushroom", ":mushroom:"], ["heart", ":heart:"], ["snowflake", ":snowflake:"], ["Africa globe", ":earth_africa:"], ["Murica globe", ":earth_americas:"], 
                                ["asia globe", ":earth_asia:"]]}

    f = SETTINGS
    if not fileIO(f, "check"):
        print("Creating default fourinarow's settings.json...")
        fileIO(f, "save", settings)

    games = {"CHANNELS": {}}

    f = GAMES
    if not fileIO(f, "check"):
        print("Creating empty game.json...")
        fileIO(f, "save", games)

    players = {"PLAYERS": {}}

    f = PLAYERS
    if not fileIO(f, "check"):
        print("Creating empty players.json...")
        fileIO(f, "save", players)

    stats = {
            "gamesStarted": 0, 
            "gamesStopped": 0, 
            "gamesRuined": 0, 
            "gamesTimedOut": 0, 
            "gamesUnlocked": 0}

    f = STATS
    if not fileIO(f, "check"):
        print("Creating empty stats.json...")
        fileIO(f, "save", stats)

class ModuleNotFound(Exception):
    def __init__(self, m):
        self.message = m
    def __str__(self):
        return self.message

def setup(bot):
    global emoji
    global logger
    check_folders()
    check_files()
    logger = logging.getLogger("fourinarow")
    if logger.level == 0: # Prevents the logger from being loaded again in case of module reload
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler(filename=LOGGER, encoding='utf-8', mode='a')
        handler.setFormatter(logging.Formatter('%(asctime)s %(message)s', datefmt="[%d/%m/%Y %H:%M]"))
        logger.addHandler(handler)
    try:
        import emoji    
        """The max amount of ':thumbsdown:' in one chat message = x166 with len2000 as max. allowed for msg. When using bytewise 👎 / Unicode instead, it becomes x1999.
            Most of these are supported by Discord http://www.emoji-cheat-sheet.com == https://github.com/carpedm20/emoji '\Python35\Lib\site-packages\emoji\\unicode_codes.py'
            *No need to modify the UFT-8 dataIO.py or store and manually maintain the modest array of all Unicode emoji in this script itself."""
    except:
        raise ModuleNotFound("emoji is not installed. Do 'pip3 install emoji --upgrade' to use this cog.")
    bot.add_cog(FourInARow(bot))
    logger.info("----Game Reloaded----")


