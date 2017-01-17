import discord
from discord.ext import commands
from discord.utils import find
from __main__ import send_cmd_help
import platform, asyncio, string, operator, random, textwrap
import os, re, aiohttp
from .utils.dataIO import fileIO
from cogs.utils import checks
try:
    import scipy
    import scipy.misc
    import scipy.cluster
except:
    pass

try:
    from PIL import Image, ImageDraw, ImageFont, ImageColor, ImageOps
except:
    raise RuntimeError("You don't have pillow installed. run 'pip3 install pillow' and try again")
import time

# fonts
font_file = 'data/leveler/fonts/font.ttf'
font_bold_file = 'data/leveler/fonts/font_bold.ttf'
font_unicode_file = 'data/leveler/fonts/unicode.ttf'

# Credits (None)
bg_credits = {

}

# directory
user_directory = "data/leveler/users"

prefix = fileIO("data/marvin/settings.json", "load")['PREFIXES']
default_avatar_url = "http://puu.sh/qB89K/c37cd0de38.jpg"

class Leveler:
    """A level up thing with image generation!"""

    def __init__(self, bot):
        self.bot = bot
        self.backgrounds = fileIO("data/leveler/backgrounds.json", "load")
        self.badges = fileIO("data/leveler/badges.json", "load")
        self.settings = fileIO("data/leveler/settings.json", "load")
        bot_settings = fileIO("data/marvin/settings.json", "load")
        self.owner = bot_settings["OWNER"]

    @commands.command(pass_context=True, no_pm=True)
    async def profile(self,ctx, *, user : discord.Member=None):
        """Displays a user profile."""
        if user == None:
            user = ctx.message.author
        channel = ctx.message.channel
        server = user.server
        curr_time = time.time()
        # creates user if doesn't exist
        await self._create_user(user, server)
        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")

        if server.id in self.settings["disabled_servers"]:
            await self.bot.say("**Leveler commands for this server are disabled!**")
            return

        if "text_only" in self.settings and server.id in self.settings["text_only"]:
            em = await self.profile_text(user, server, userinfo)
            await self.bot.send_message(channel, '', embed = em)
        else :
            if "profile_block" not in userinfo:
                userinfo["profile_block"] = 0

            cooldown = 10
            elapsed_time = curr_time - userinfo["profile_block"]
            if elapsed_time > cooldown:
                await self.draw_profile(user, server)
                await self.bot.send_typing(channel)         
                await self.bot.send_file(channel, 'data/leveler/users/{}/profile.png'.format(user.id), content='**User profile for {}**'.format(self._is_mention(user)))
                userinfo["profile_block"] = curr_time
                fileIO('data/leveler/users/{}/info.json'.format(user.id), "save", userinfo)
            else:
                await self.bot.say("**{}, please wait. {}s Cooldown!**".format(self._is_mention(user), int(cooldown - elapsed_time)))

    async def profile_text(self, user, server, userinfo):
        def test_empty(text):
            if text == '':
                return "None"
            else:
                return text

        em = discord.Embed(description='', colour=user.colour)
        em.add_field(name="Title:", value = test_empty(userinfo["title"]))
        em.add_field(name="Reps:", value= userinfo["rep"])
        em.add_field(name="Global Rank:", value = await self._find_global_rank(user, server))
        em.add_field(name="Server Rank:", value = await self._find_server_rank(user, server))
        em.add_field(name="Server Level:", value = format(userinfo["servers"][server.id]["level"]))
        em.add_field(name="Total Exp:", value = userinfo["total_exp"])
        total_server_exp = 0
        for i in range(userinfo["servers"][server.id]["level"]):
            total_server_exp += self._required_exp(i)
        total_server_exp += userinfo["servers"][server.id]["current_exp"]
        em.add_field(name="Server Exp:", value = format(total_server_exp))
        try:
            bank = self.bot.get_cog('Economy').bank
            if bank.account_exists(user):
                credits = bank.get_balance(user)
            else:
                credits = 0
        except:
            credits = 0
        em.add_field(name="Towels: ", value = format(credits))
        em.add_field(name="Info: ", value = test_empty(userinfo["info"]))
        em.add_field(name="Badges: ", value = test_empty(", ".join(userinfo["badges"])))
        em.set_author(name="User profile for {}".format(user.name), url=user.avatar_url, icon_url=user.avatar_url)
        return em

    @commands.command(pass_context=True, no_pm=True)
    async def rank(self,ctx,user : discord.Member=None):
        """Displays the rank of a user."""
        if user == None:
            user = ctx.message.author
        channel = ctx.message.channel
        server = user.server
        curr_time = time.time()
        # creates user if doesn't exist
        await self._create_user(user, server)
        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")

        if server.id in self.settings["disabled_servers"]:
            await self.bot.say("**Leveler commands for this server are disabled!**")
            return

        if "text_only" in self.settings and server.id in self.settings["text_only"]:
            em = await self.rank_text(user, server)
            await self.bot.send_message(channel, '', embed = em)
        else:
            if "rank_block" not in userinfo:
                userinfo["rank_block"] = 0

            cooldown = 10
            elapsed_time = curr_time - userinfo["rank_block"]
            if elapsed_time > cooldown:
                await self.draw_rank(user, server)
                await self.bot.send_typing(channel)            
                await self.bot.send_file(channel, 'data/leveler/users/{}/rank.png'.format(user.id), content='**Ranking & Statistics for {}**'.format(self._is_mention(user)))
                userinfo["rank_block"] = curr_time
                fileIO('data/leveler/users/{}/info.json'.format(user.id), "save", userinfo)
            else:
                await self.bot.say("**{}, please wait. {}s Cooldown!**".format(self._is_mention(user), int(cooldown - elapsed_time))) 

    async def rank_text(self, user, server):
        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")
        em = discord.Embed(description='', colour=user.colour)
        em.add_field(name="Server Rank", value = await self._find_server_rank(user, server))
        em.add_field(name="Reps", value = userinfo["rep"])
        em.add_field(name="Server Level", value = userinfo["servers"][server.id]["level"])
        total_server_exp = 0
        for i in range(userinfo["servers"][server.id]["level"]):
            total_server_exp += self._required_exp(i)
        total_server_exp += userinfo["servers"][server.id]["current_exp"]
        em.add_field(name="Server Exp", value = total_server_exp)
        em.set_author(name="Rank and Statistics for {}".format(user.name), url=user.avatar_url, icon_url=user.avatar_url)
        return em

    # should the user be mentioned based on settings?
    def _is_mention(self,user):
        if "mention" not in self.settings.keys() or self.settings["mention"]:
            return user.mention
        else:
            return user.name

    @commands.command(pass_context=True, no_pm=True)
    async def top10(self,ctx, global_rank:str = None):
        '''Displays leaderboard. Add "global" parameter for global'''
        server = ctx.message.server

        if server.id in self.settings["disabled_servers"]:
            await self.bot.say("**Leveler commands for this server are disabled!**")
            return

        users = []
        if global_rank == "global":
            msg = "**Global Leaderboard for {}**\n".format(self.bot.user.name)
            # this is also terrible...
            for userid in os.listdir(user_directory):
                userinfo = fileIO("data/leveler/users/{}/info.json".format(userid), "load")
                for server in self.bot.servers:
                    temp_user = find(lambda m: m.id == userid, server.members)
                    if temp_user != None:
                        break
                if temp_user != None:
                    users.append((temp_user.name, userinfo["total_exp"]))
            sorted_list = sorted(users, key=operator.itemgetter(1), reverse=True)
        else:
            msg = "**Leaderboard for {}**\n".format(server.name)
            for userid in os.listdir(user_directory):
                userinfo = fileIO("data/leveler/users/{}/info.json".format(userid), "load")                
                if "servers" in userinfo and server.id in userinfo["servers"]:
                    temp_user = find(lambda m: m.id == userid, server.members)
                    server_exp = 0
                    for i in range(userinfo["servers"][server.id]["level"]):
                        server_exp += self._required_exp(i)
                    server_exp +=  userinfo["servers"][server.id]["current_exp"]
                    if temp_user != None:
                        users.append((temp_user.name, server_exp))
            sorted_list = sorted(users, key=operator.itemgetter(1), reverse=True)

        msg += "```ruby\n"
        rank = 1
        labels = ["♔", "♕", "♖", "♗", "♘", "♙", " ", " ", " ", " "]
        for user in sorted_list[:10]:
            msg += u'{:<2}{:<2}{:<2}   # {:<5}\n'.format(rank, labels[rank-1], u"➤", user[0])
            msg += u'{:<2}{:<2}{:<2}    {:<5}\n'.format(" ", " ", " ", "Total Points: " + str(user[1]))
            rank += 1
        msg +="```"
        await self.bot.say(msg)       

    @commands.command(pass_context=True, no_pm=True)
    async def rep(self, ctx, user : discord.Member):
        """Gives a reputation point to a designated player."""
        channel = ctx.message.channel
        server = user.server
        org_user = ctx.message.author
        # creates user if doesn't exist
        await self._create_user(org_user, server)
        await self._create_user(user, server)
        org_userinfo = fileIO("data/leveler/users/{}/info.json".format(org_user.id), "load")
        curr_time = time.time()
        
        if server.id in self.settings["disabled_servers"]:
            await self.bot.say("**Leveler commands for this server are disabled!**")
            return
        if user.id == org_user.id:
            await self.bot.say("**You can't give a rep to yourself!**")
            return
        if user.bot:
            await self.bot.say("**You can't give a rep to a bot!**")
            return
        if "rep_block" not in org_userinfo:
            org_userinfo["rep_block"] = 0

            fileIO("data/leveler/users/{}/info.json".format(org_user.id), "save", org_userinfo)

        delta = float(curr_time) - float(org_userinfo["rep_block"])
        if delta >= 43200.0 and delta>0:
            userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")
            org_userinfo["rep_block"] = curr_time
            userinfo["rep"] += 1
            fileIO("data/leveler/users/{}/info.json".format(org_user.id), "save", org_userinfo)
            fileIO("data/leveler/users/{}/info.json".format(user.id), "save", userinfo)
            await self.bot.say("**You have just given {} a reputation point!**".format(self._is_mention(user)))
        else:
            # calulate time left
            seconds = 43200 - delta
            m, s = divmod(seconds, 60)
            h, m = divmod(m, 60)
            await self.bot.say("**You need to wait {} hours, {} minutes, and {} seconds until you can give reputation again!**".format(int(h), int(m), int(s)))
    
    @commands.command(pass_context=True, no_pm=True)
    async def profileinfo(self, ctx, user : discord.Member = None):
        """Gives more specific details about user profile image."""

        if not user:
            user = ctx.message.author
        server = ctx.message.server
        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")

        server = ctx.message.server
        
        if server.id in self.settings["disabled_servers"]:
            await self.bot.say("**Leveler commands for this server are disabled!**")
            return

        # creates user if doesn't exist
        await self._create_user(user, server)

        msg = "```xl\n"
        msg += "Name: {}\n".format(user.name)
        msg += "Title: {}\n".format(userinfo["title"])
        msg += "Reps: {}\n".format(userinfo["rep"])
        msg += "Server Level: {}\n".format(userinfo["servers"][server.id]["level"])
        total_server_exp = 0
        for i in range(userinfo["servers"][server.id]["level"]):
            total_server_exp += self._required_exp(i)
        total_server_exp += userinfo["servers"][server.id]["current_exp"]
        msg += "Server Exp: {}\n".format(total_server_exp)
        msg += "Total Exp: {}\n".format(userinfo["total_exp"])
        msg += "Info: {}\n".format(userinfo["info"])
        msg += "Profile background: {}\n".format(userinfo["profile_background"])
        msg += "Rank background: {}\n".format(userinfo["rank_background"])
        msg += "Levelup background: {}\n".format(userinfo["levelup_background"])
        if "rep_color" in userinfo.keys() and userinfo["rep_color"]:
            msg += "Rep section color: {}\n".format(self._rgb_to_hex(userinfo["rep_color"]))
        if "badge_col_color" in userinfo.keys() and userinfo["badge_col_color"]:
            msg += "Badge section color: {}\n".format(self._rgb_to_hex(userinfo["badge_col_color"]))
        if "profile_exp_color" in userinfo.keys() and userinfo["profile_exp_color"]:
            msg += "Profile exp color: {}\n".format(self._rgb_to_hex(userinfo["profile_exp_color"]))
        if "rank_exp_color" in userinfo.keys() and userinfo["rank_exp_color"]:
            msg += "Rank exp color: {}\n".format(self._rgb_to_hex(userinfo["rank_exp_color"]))
        msg += "Badges: "
        msg += ", ".join(userinfo["badges"])
        msg += "```"
        await self.bot.say(msg)

    def _rgb_to_hex(self, rgb):
        rgb = tuple(rgb[:3])
        return '#%02x%02x%02x' % rgb

    @commands.group(pass_context=True)
    async def lvlset(self, ctx):
        """Profile Configuration Options"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return
            
    @lvlset.command(pass_context=True, no_pm=True)
    async def listbgs(self, ctx):
        '''Gives a list of backgrounds.'''
        server = ctx.message.server

        if server.id in self.settings["disabled_servers"]:
            await self.bot.say("**Leveler commands for this server are disabled!**")
            return

        msg = ""
        for category in self.backgrounds.keys():
            msg += "**{}**".format(category.upper())
            msg += "```ruby\n"
            msg += ", ".join(sorted(self.backgrounds[category].keys()))
            msg += "```\n"
        await self.bot.say(msg)

    @commands.cooldown(rate = '1', per = '3')
    @lvlset.command(pass_context=True, no_pm=True)
    async def sidebar(self, ctx, rep_color:str, badge_col_color:str):
        """Set sidebar colors and accents. 'auto': according to current bg."""
        user = ctx.message.author
        server = ctx.message.server
        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")

        if server.id in self.settings["disabled_servers"]:
            await self.bot.say("**Leveler commands for this server are disabled!**")
            return

        if "text_only" in self.settings and server.id in self.settings["text_only"]:
            await self.bot.say("**Text-only commands allowed.**")
            return

        default_rep = (92,130,203,230)
        default_badge_col = (128,151,165,230)
        default_a = 230
        valid = True
        hex_color = None
        rep_rank = int(random.randint(2,3))
        color_ranks = [rep_rank, 0] # adds some randomness to rep color + most prominent color

        # creates user if doesn't exist
        await self._create_user(user, server)

        # still ugly, might fix later
        if rep_color == "auto":
            hex_color = await self._auto_color(userinfo["profile_background"], color_ranks)
            color = self._hex_to_rgb(hex_color[0], default_a)
            color = self._moderate_color(color, default_a, 5)
            userinfo["rep_color"] = color                 
        elif rep_color == "default":
            userinfo["rep_color"] = default_rep
        elif self._is_hex(rep_color):
            userinfo["rep_color"] = self._hex_to_rgb(rep_color, default_a)
        else: 
            await self.bot.say("**That's not a valid rep color!**")
            valid = False

        if badge_col_color == "auto":
            if hex_color != None:
                hex_color = hex_color[1] # grabs the other color
            else:
                hex_color = await self._auto_color(userinfo["profile_background"], [0])
                hex_color = hex_color[0] 
            color = self._hex_to_rgb(hex_color, default_a)
            color = self._moderate_color(color, default_a, 15)           
            userinfo["badge_col_color"] = color
        elif badge_col_color == "default":
            userinfo["badge_col_color"] = default_badge_col
        elif self._is_hex(badge_col_color):
            userinfo["badge_col_color"] = self._hex_to_rgb(badge_col_color, default_a)
        else: 
            await self.bot.say("**That's not a valid badge column color!**")
            valid = False

        if valid:
            await self.bot.say("**{}, your sidebar colors have been set!**".format(self._is_mention(user)))
            fileIO("data/leveler/users/{}/info.json".format(user.id), "save", userinfo)

    @lvlset.command(pass_context=True, no_pm=True)
    async def profileexp(self, ctx, exp_color:str):
        """Set profile exp color. 'auto': according to current bg."""
        user = ctx.message.author
        server = ctx.message.server
        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")
        default_exp = (255, 255, 255, 230)
        default_a = 230
        valid = True
        color_rank = int(random.randint(2,3))

        if server.id in self.settings["disabled_servers"]:
            await self.bot.say("Leveler commands for this server are disabled.")
            return

        if "text_only" in self.settings and server.id in self.settings["text_only"]:
            await self.bot.say("**Text-only commands allowed.**")
            return

        # creates user if doesn't exist
        await self._create_user(user, server)

        if exp_color == "auto":
            hex_color = await self._auto_color(userinfo["profile_background"], [color_rank])
            color = self._hex_to_rgb(hex_color[0], default_a)
            color = self._moderate_color(color, default_a, 0)
            userinfo["profile_exp_color"] = color                 
        elif exp_color == "default":
            userinfo["profile_exp_color"] = default_exp
        elif self._is_hex(exp_color):
            userinfo["profile_exp_color"] = self._hex_to_rgb(exp_color, default_a)
        else: 
            await self.bot.say("**That's not a valid exp color!**")
            valid = False

        if valid:
            await self.bot.say("**{}, your profile exp colors have been set!**".format(self._is_mention(user)))
            fileIO("data/leveler/users/{}/info.json".format(user.id), "save", userinfo)

    @lvlset.command(pass_context=True, no_pm=True)
    async def rankexp(self, ctx, exp_color:str):
        """Set rank exp color. 'auto': according to current bg."""
        user = ctx.message.author
        server = ctx.message.server
        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")
        default_exp = (255, 255, 255, 230)
        default_a = 230
        valid = True
        color_rank = int(random.randint(2,3))
        
        if server.id in self.settings["disabled_servers"]:
            await self.bot.say("Leveler commands for this server are disabled.")
            return

        if "text_only" in self.settings and server.id in self.settings["text_only"]:
            await self.bot.say("**Text-only commands allowed.**")
            return

        # creates user if doesn't exist
        await self._create_user(user, server)

        if exp_color == "auto":
            hex_color = await self._auto_color(userinfo["rank_background"], [color_rank])
            color = self._hex_to_rgb(hex_color[0], default_a)
            color = self._moderate_color(color, default_a, 0)
            userinfo["rank_exp_color"] = color          
        elif exp_color == "default":
            userinfo["rank_exp_color"] = default_exp
        elif self._is_hex(exp_color):
            userinfo["rank_exp_color"] = self._hex_to_rgb(exp_color, default_a)
        else: 
            await self.bot.say("**That's not a valid exp color!**")
            valid = False

        if valid:
            await self.bot.say("**{}, your rank exp colors have been set!**".format(self._is_mention(user)))
            fileIO("data/leveler/users/{}/info.json".format(user.id), "save", userinfo)

    # uses k-means algorithm to find color from bg, rank is abundance of color, descending
    async def _auto_color(self, url:str, ranks):
        phrases = ["Calculating colors..."] # in case I want more
        try:
            await self.bot.say("**{}**".format(random.choice(phrases)))   
            clusters = 10

            async with aiohttp.get(url) as r:
                image = await r.content.read()
            with open('data/leveler/temp_auto.png','wb') as f:
                f.write(image)

            im = Image.open('data/leveler/temp_auto.png').convert('RGBA')            
            im = im.resize((290, 290)) # resized to reduce time
            ar = scipy.misc.fromimage(im)
            shape = ar.shape
            ar = ar.reshape(scipy.product(shape[:2]), shape[2])

            codes, dist = scipy.cluster.vq.kmeans(ar.astype(float), clusters)
            vecs, dist = scipy.cluster.vq.vq(ar, codes)         # assign codes
            counts, bins = scipy.histogram(vecs, len(codes))    # count occurrences

            # sort counts
            freq_index = []
            index = 0
            for count in counts:
                freq_index.append((index, count))
                index += 1
            sorted_list = sorted(freq_index, key=operator.itemgetter(1), reverse=True)

            colors = []
            for rank in ranks:
                color_index = min(rank, len(codes))
                peak = codes[sorted_list[color_index][0]] # gets the original index
                peak = peak.astype(int)

                colors.append(''.join(format(c, '02x') for c in peak))
            return colors # returns array
        except:
            await self.bot.say("```Error or no scipy. Install scipy doing 'pip3 install numpy' and 'pip3 install scipy' or read here: https://github.com/AznStevy/Maybe-Useful-Cogs/blob/master/README.md```")           

    # converts hex to rgb
    def _hex_to_rgb(self, hex_num: str, a:int):
        h = hex_num.lstrip('#')

        # if only 3 characters are given
        if len(str(h)) == 3:
            expand = ''.join([x*2 for x in str(h)])
            h = expand

        colors = [int(h[i:i+2], 16) for i in (0, 2 ,4)]
        colors.append(a)
        return tuple(colors)

    # dampens the color given a parameter
    def _moderate_color(self, rgb, a, moderate_num):
        new_colors = []
        for color in rgb[:3]:
            if color > 128:
                color -= moderate_num
            else:
                color += moderate_num
            new_colors.append(color)
        new_colors.append(230)

        return tuple(new_colors)


    @lvlset.command(pass_context=True, no_pm=True)
    async def info(self, ctx, *, info):
        """Set your user info."""
        user = ctx.message.author
        server = ctx.message.server
        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")
        max_char = 150

        if server.id in self.settings["disabled_servers"]:
            await self.bot.say("Leveler commands for this server are disabled.")
            return

        # creates user if doesn't exist
        await self._create_user(user, server)

        if len(info) < max_char:
            userinfo["info"] = info
            fileIO("data/leveler/users/{}/info.json".format(user.id), "save", userinfo)
            await self.bot.say("**Your info section has been succesfully set!**")
        else:
            await self.bot.say("**Your description has too many characters! Must be <{}**".format(max_char))

    @lvlset.command(pass_context=True, no_pm=True)
    async def levelbg(self, ctx, *, image_name:str):
        """Set your level background"""
        user = ctx.message.author
        server = ctx.message.server
        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")        

        if server.id in self.settings["disabled_servers"]:
            await self.bot.say("Leveler commands for this server are disabled.")
            return

        if "text_only" in self.settings and server.id in self.settings["text_only"]:
            await self.bot.say("**Text-only commands allowed.**")
            return            

        # creates user if doesn't exist
        await self._create_user(user, server)

        if image_name in self.backgrounds["levelup"].keys():
            if await self._process_purchase(ctx):
                userinfo["levelup_background"] = self.backgrounds["levelup"][image_name]
                fileIO("data/leveler/users/{}/info.json".format(user.id), "save", userinfo)
                await self.bot.say("**Your new level-up background has been succesfully set!**")
        else:
            await self.bot.say("That is not a valid bg. See available bgs at {}lvlset listbgs".format(prefix))

    @lvlset.command(pass_context=True, no_pm=True)
    async def profilebg(self, ctx, *, image_name:str):
        """Set your profile background"""
        user = ctx.message.author
        server = ctx.message.server
        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")

        if server.id in self.settings["disabled_servers"]:
            await self.bot.say("Leveler commands for this server are disabled.")
            return

        if "text_only" in self.settings and server.id in self.settings["text_only"]:
            await self.bot.say("**Text-only commands allowed.**")
            return

        # creates user if doesn't exist
        await self._create_user(user, server)

        if image_name in self.backgrounds["profile"].keys():
            if await self._process_purchase(ctx):
                userinfo["profile_background"] = self.backgrounds["profile"][image_name]
                fileIO("data/leveler/users/{}/info.json".format(user.id), "save", userinfo)
                await self.bot.say("**Your new profile background has been succesfully set!**")
        else:
            await self.bot.say("That is not a valid bg. See available bgs at {}lvlset listbgs".format(prefix))

    @lvlset.command(pass_context=True, no_pm=True)
    async def rankbg(self, ctx, *, image_name:str):
        """Set your rank background"""
        user = ctx.message.author
        server = ctx.message.server
        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")

        if server.id in self.settings["disabled_servers"]:
            await self.bot.say("Leveler commands for this server are disabled.")
            return

        if "text_only" in self.settings and server.id in self.settings["text_only"]:
            await self.bot.say("**Text-only commands allowed.**")
            return
            
        # creates user if doesn't exist
        await self._create_user(user, server)

        if image_name in self.backgrounds["rank"].keys():
            if await self._process_purchase(ctx):
                userinfo["rank_background"] = self.backgrounds["rank"][image_name]
                fileIO("data/leveler/users/{}/info.json".format(user.id), "save", userinfo)
                await self.bot.say("**Your new rank background has been succesfully set!**")
        else:
            await self.bot.say("That is not a valid bg. See available bgs at {}lvlset listbgs".format(prefix))

    @lvlset.command(pass_context=True, no_pm=True)
    async def title(self, ctx, *, title):
        """Set your title."""
        user = ctx.message.author
        server = ctx.message.server
        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")
        max_char = 20

        if server.id in self.settings["disabled_servers"]:
            await self.bot.say("Leveler commands for this server are disabled.")
            return

        # creates user if doesn't exist
        await self._create_user(user, server)

        if len(title) < max_char:
            userinfo["title"] = title
            fileIO("data/leveler/users/{}/info.json".format(user.id), "save", userinfo)
            await self.bot.say("**Your title has been succesfully set!**")
        else:
            await self.bot.say("**Your title has too many characters! Must be <{}**".format(max_char))

    @checks.admin_or_permissions(manage_server=True)
    @commands.group(pass_context=True)
    async def lvladmin(self, ctx):
        """Admin Toggle Features"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return

    @checks.admin_or_permissions(manage_server=True)
    @lvladmin.command(pass_context=True, no_pm=True)
    async def overview(self, ctx):
        """A list of settings"""
        disabled_servers = []
        private_levels = []
        disabled_levels = []
        locked_channels = []

        for server in self.bot.servers:
            if "disabled_servers" in self.settings.keys() and server.id in self.settings["disabled_servers"]:
                disabled_servers.append(server.name)
            if "lvl_msg_lock" in self.settings.keys() and server.id in self.settings["lvl_msg_lock"].keys():
                for channel in server.channels:
                    if self.settings["lvl_msg_lock"][server.id] == channel.id:
                        locked_channels.append("\n{} -> #{}".format(server.name,channel.name))
                disabled_servers.append(server.name)
            if "lvl_msg" in self.settings.keys() and server.id in self.settings["lvl_msg"]:
                disabled_levels.append(server.name)
            if "private_lvl_msg" in self.settings.keys() and server.id in self.settings["private_lvl_msg"]:
                private_levels.append(server.name)

        msg = "```xl\n"
        if "mention" in self.settings.keys():
            msg += "Mentions: {}\n".format(str(self.settings["mention"]))
        msg += "Background Price: {}\n".format(self.settings["bg_price"])
        if "badge_type" in self.settings.keys():
            msg += "Badge type: {}\n".format(self.settings["badge_type"])
        msg += "Disabled Servers: {}\n".format(", ".join(disabled_servers))
        msg += "Disabled Level Messages: {}\n".format(", ".join(disabled_levels))
        msg += "Private Level Messages: {}\n".format(", ".join(private_levels))
        msg += "Channel Locks: {}\n".format(", ".join(locked_channels))
        msg += "```"
        await self.bot.say(msg)



    @lvladmin.command(pass_context=True, no_pm=True)
    async def lvlmsglock(self, ctx):
        '''Locks levelup messages to one channel. Disable command on locked channel.'''
        channel = ctx.message.channel
        server = ctx.message.server

        if "lvl_msg_lock" not in self.settings.keys():
            self.settings["lvl_msg_lock"] = {}

        if server.id in self.settings["lvl_msg_lock"]:
            if channel.id == self.settings["lvl_msg_lock"][server.id]:
                del self.settings["lvl_msg_lock"][server.id]
                await self.bot.say("**Level-up message lock disabled.**".format(channel.name))
            else:
                self.settings["lvl_msg_lock"][server.id] = channel.id
                await self.bot.say("**Level-up message lock changed to #{}.**".format(channel.name))
        else:
            self.settings["lvl_msg_lock"][server.id] = channel.id
            await self.bot.say("**Level-up messages locked to #{}**".format(channel.name))

        fileIO('data/leveler/settings.json', "save", self.settings)

    async def _process_purchase(self, ctx):
        user = ctx.message.author
        server = ctx.message.server

        try:
            bank = self.bot.get_cog('Economy').bank
            if bank.account_exists(user):
                if not bank.can_spend(user, self.settings["bg_price"]):
                    await self.bot.say("**Insufficient funds. Backgrounds changes cost: ${}**".format(self.settings["bg_price"]))
                    return False
                else:
                    new_balance = bank.get_balance(user) - self.settings["bg_price"]
                    bank.set_credits(user, new_balance)
                    return True            
            else:
                if self.settings["bg_price"] == 0:
                    return True
                else:
                    await self.bot.say("**You don't have an account. Do {}bank register**".format(prefix))
                    return False
        except:
            if self.settings["bg_price"] == 0:
                return True
            else:
                await self.bot.say("**There was an error with economy cog. Fix to allow purchases or set price to $0. Currently ${}**".format(prefix, self.settings["bg_price"]))
                return False           

    @checks.is_owner()
    @lvladmin.command(no_pm=True)
    async def setprice(self, price:int):
        '''Set a price for background changes.'''
        if price < 0:
            await self.bot.say("**That is not a valid background price.**")
        else:
            self.settings["bg_price"] = price
            await self.bot.say("**Background price set to: $`{}`!**".format(price))
            fileIO('data/leveler/settings.json', "save", self.settings)

    @checks.is_owner()
    @lvladmin.command(pass_context=True, no_pm=True)
    async def setlevel(self, ctx, user : discord.Member, level:int):
        '''Set a user's level. (What a cheater c:).'''
        org_user = ctx.message.author
        server = user.server
        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")

        if server.id in self.settings["disabled_servers"]:
            await self.bot.say("Leveler commands for this server are disabled.")
            return

        if level < 0:
            await self.bot.say("**Please enter a positive number.**")
            return
            
        # creates user if doesn't exist
        await self._create_user(user, server)

        # get rid of old level exp
        old_server_exp = 0
        for i in range(userinfo["servers"][server.id]["level"]):
            old_server_exp += self._required_exp(i)
        userinfo["total_exp"] -= old_server_exp
        userinfo["total_exp"] -= userinfo["servers"][server.id]["current_exp"]

        # add in new exp
        total_exp = 0
        for i in range(level):
            total_exp += self._required_exp(i)
        userinfo["servers"][server.id]["current_exp"] = 0
        userinfo["servers"][server.id]["level"] = level
        userinfo["total_exp"] += total_exp

        fileIO("data/leveler/users/{}/info.json".format(user.id), "save", userinfo)
        await self.bot.say("**{}'s Level has been set to {}.**".format(self._is_mention(user), level))

    @checks.is_owner()
    @lvladmin.command(no_pm=True)
    async def mention(self):
        '''Toggle mentions on messages.'''
        if "mention" not in self.settings.keys() or self.settings["mention"] == True:
            self.settings["mention"] = False
            await self.bot.say("**Mentions disabled.**")
        else:
            self.settings["mention"] = True
            await self.bot.say("**Mentions enabled.**")
        fileIO('data/leveler/settings.json', "save", self.settings)

    async def _valid_image_url(self, url):
        max_byte = 1000

        try:
            async with aiohttp.get(url) as r:
                image = await r.content.read()
            with open('data/leveler/test.png','wb') as f:
                f.write(image)
            image = Image.open('data/leveler/test.png').convert('RGBA')
            os.remove('data/leveler/test.png')
            return True
        except:          
            return False

    @checks.admin_or_permissions(manage_server=True)
    @lvladmin.command(pass_context=True, no_pm=True)
    async def toggle(self, ctx):
        """Toggle most leveler commands on the current server."""
        server = ctx.message.server
        if server.id in self.settings["disabled_servers"]:
            self.settings["disabled_servers"].remove(server.id)
            await self.bot.say("**Leveler enabled on {}.**".format(server.name))
        else:
            self.settings["disabled_servers"].append(server.id)
            await self.bot.say("**Leveler disabled on {}.**".format(server.name))
        fileIO('data/leveler/settings.json', "save", self.settings)

    @checks.admin_or_permissions(manage_server=True)
    @lvladmin.command(pass_context = True, no_pm=True)
    async def textonly(self, ctx, all:str=None):
        """Toggle text-based messages on the server. Parameter: disableall/enableall"""
        server = ctx.message.server
        user = ctx.message.author
        # deals with enabled array

        if "text_only" not in self.settings.keys():
            self.settings["text_only"] = [] 

        if all != None:
            if user.id == self.owner:
                if all == "disableall":
                    self.settings["text_only"] = []
                    await self.bot.say("**Text-only disabled for all servers.**")
                elif all == "enableall":
                    self.settings["lvl_msg"] = []
                    for server in self.bot.servers:
                        self.settings["text_only"].append(server.id)
                    await self.bot.say("**Text-only messages enabled for all servers.**")
            else:
                await self.bot.say("**No Permission.**")                
        else:
            if server.id in self.settings["text_only"]:
                self.settings["text_only"].remove(server.id)
                await self.bot.say("**Text-only messages disabled for {}.**".format(server.name))
            else:
                self.settings["text_only"].append(server.id)
                await self.bot.say("**Text-only messages enabled for {}.**".format(server.name)) 
        fileIO('data/leveler/settings.json', "save", self.settings)

    @checks.admin_or_permissions(manage_server=True)
    @lvladmin.command(pass_context = True, no_pm=True)
    async def lvlalert(self, ctx, all:str=None):
        """Toggle level-up messages on the server. Parameter: disableall/enableall"""
        server = ctx.message.server
        # deals with enabled array

        # old version was boolean
        if not isinstance(self.settings["lvl_msg"], list):
            self.settings["lvl_msg"] = []

        if all != None:
            if user.id == self.owner:
                if all == "disableall":
                    self.settings["lvl_msg"] = []
                    await self.bot.say("**Level-up messages disabled for all servers.**")
                elif all == "enableall":
                    self.settings["lvl_msg"] = []
                    for server in self.bot.servers:
                        self.settings["lvl_msg"].append(server.id)
                    await self.bot.say("**Level-up messages enabled for all servers.**")
            else:
                await self.bot.say("**No Permission.**")
        else:
            if server.id in self.settings["lvl_msg"]:
                self.settings["lvl_msg"].remove(server.id)
                await self.bot.say("**Level-up messages disabled for {}.**".format(server.name))
            else:
                self.settings["lvl_msg"].append(server.id)
                await self.bot.say("**Level-up messages enabled for {}.**".format(server.name)) 
        fileIO('data/leveler/settings.json', "save", self.settings)

    @checks.admin_or_permissions(manage_server=True)
    @lvladmin.command(pass_context = True, no_pm=True)
    async def lvlprivate(self, ctx, all:str=None):
        """Toggles if lvl alert is a private message to the user."""
        server = ctx.message.server
        # deals with ENABLED array, not disabled

        if "private_lvl_msg" not in self.settings.keys():
            self.settings["private_lvl_msg"] = [] 

        if all != None:
            if user.id == self.owner:
                if all == "disableall":
                    self.settings["private_lvl_msg"] = []
                    await self.bot.say("**Private level-up messages disabled for all servers.**")
                elif all == "enableall":
                    self.settings["private_lvl_msg"] = []
                    for server in self.bot.servers:
                        self.settings["private_lvl_msg"].append(server.id)
                    await self.bot.say("**Private level-up messages enabled for all servers.**")
            else:
                await self.bot.say("**No Permission.**")
        else:
            if server.id in self.settings["private_lvl_msg"]:
                self.settings["private_lvl_msg"].remove(server.id)
                await self.bot.say("**Private level-up messages disabled for {}.**".format(server.name))
            else:
                self.settings["private_lvl_msg"].append(server.id)
                await self.bot.say("**Private level-up messages enabled for {}.**".format(server.name))

        fileIO('data/leveler/settings.json', "save", self.settings)             

    @commands.group(pass_context=True)
    async def lvlbadge(self, ctx):
        """Badge Configuration Options"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return

    @lvlbadge.command(pass_context=True, no_pm=True)
    async def listbadges(self, ctx):
        '''Get a list of badges.'''
        msg = "```xl\n"
        for badge in self.badges.keys():
            msg += "+ {}\n".format(badge)
        msg += "```"
        await self.bot.say(msg)  

    @checks.admin_or_permissions(manage_server=True)
    @lvlbadge.command(no_pm=True)
    async def addbadge(self, name:str, priority_num: int, text_color:str, bg_color:str, border_color:str = None):
        """Add a badge. Colors in hex, border color optional."""

        if not self._is_hex(text_color):
            await self.bot.say("**Text color hex is not valid!**")
            return

        if not self._is_hex(bg_color) and not await self._valid_image_url(bg_color):
            await self.bot.say("**Backround is not valid. Enter hex or image url!**")
            return

        if not border_color and self._is_hex(border_color):
            await self.bot.say("**Border color is not valid!**")
            return

        if name in self.badges:
            await self.bot.say("**{} badge updated.**".format(name))
        else:
            await self.bot.say("**{} badge added.**".format(name))

        self.badges[name] = {
            "priority_num": priority_num,
            "text_color" : text_color,
            "bg_color": bg_color,
            "border_color": border_color
        }

        fileIO('data/leveler/badges.json', "save", self.badges)

    @checks.admin_or_permissions(manage_server=True)
    @lvlbadge.command(no_pm=True)
    async def type(self, name:str):
        """circles, bars, or squares. All lowercase."""
        valid_types = ["circles", "bars", "squares"]
        if name.lower() not in valid_types:
            await self.bot.say("**That is not a valid badge type!**")
            return 

        self.settings["badge_type"] = name.lower()
        await self.bot.say("**Badge type set to {}**".format(name.lower()))
        fileIO('data/leveler/settings.json', "save", self.settings)

    def _is_hex(self, color:str):
        if color != None and len(color) != 4 and len(color) != 7:
            return False

        reg_ex = r'^#(?:[0-9a-fA-F]{3}){1,2}$'
        return re.search(reg_ex, str(color))

    @checks.admin_or_permissions(manage_server=True)
    @lvlbadge.command(pass_context = True, no_pm=True)
    async def delbadge(self, ctx, name:str):
        """Delete a badge and remove from all users."""
        user = ctx.message.author
        channel = ctx.message.channel
        server = user.server

        # creates user if doesn't exist
        await self._create_user(user, server)

        if server.id in self.settings["disabled_servers"]:
            await self.bot.say("Leveler commands for this server are disabled.")
            return

        if name in self.badges:
            del self.badges[name]

            # remove the badge if there
            for userid in os.listdir(user_directory):
                userinfo = fileIO("data/leveler/users/{}/info.json".format(userid), "load")
                if name in userinfo[userid]["badges"]:
                    userinfo["badges"].remove(name)

            await self.bot.say("**The {} badge has been removed.**".format(name))
            fileIO("data/leveler/users/{}/info.json".format(userid), "save", userinfo)
            fileIO('data/leveler/badges.json', "save", self.badges)
        else:
            await self.bot.say("**That badges does not exist.**")

    @checks.admin_or_permissions(manage_server=True)
    @lvlbadge.command(pass_context = True, no_pm=True)
    async def give(self, ctx, user : discord.Member, badge_name: str):
        """Give a user a badge."""
        org_user = ctx.message.author
        server = org_user.server
        # creates user if doesn't exist
        await self._create_user(user, server)
        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")

        if server.id in self.settings["disabled_servers"]:
            await self.bot.say("Leveler commands for this server are disabled.")
            return

        if badge_name not in self.badges:
            await self.bot.say("**That badge doesn't exist!**")
        elif badge_name in userinfo["badges"]:
            await self.bot.say("**{} already has that badge!**".format(self._is_mention(user)))
        else:     
            userinfo["badges"].append(badge_name)
            fileIO("data/leveler/users/{}/info.json".format(user.id), "save", userinfo)
            await self.bot.say("**{} has just given {} the {} badge!**".format(self._is_mention(org_user), self._is_mention(user), badge_name))

    @checks.admin_or_permissions(manage_server=True)
    @lvlbadge.command(pass_context = True, no_pm=True)
    async def take(self, ctx, user : discord.Member, badge_name: str):
        """Take a user's badge."""
        org_user = ctx.message.author
        server = org_user.server
        # creates user if doesn't exist
        await self._create_user(user, server)
        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")
        if server.id in self.settings["disabled_servers"]:
            await self.bot.say("Leveler commands for this server are disabled.")
            return

        if badge_name not in self.badges:
            await self.bot.say("**That badge doesn't exist!**")
        elif badge_name not in userinfo["badges"]:
            await self.bot.say("**{} does not have that badge!**".format(self._is_mention(user)))
        else:
            userinfo["badges"].remove(badge_name)
            fileIO("data/leveler/users/{}/info.json".format(user.id), "save", userinfo)
            await self.bot.say("**{} has taken the {} badge from {}! :upside_down:**".format(self._is_mention(org_user), badge_name, self._is_mention(user)))

    @commands.group(pass_context=True)
    async def lvladminbg(self, ctx):
        """Admin Background Configuration"""
        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)
            return

    @checks.admin_or_permissions(manage_server=True)
    @lvladminbg.command(no_pm=True)
    async def addprofilebg(self, name:str, url:str):
        """Add a profile background. Proportions: (290px x 290px)"""
        if name in self.backgrounds["profile"].keys():
            await self.bot.say("**That profile background name already exists!**")
        elif not await self._valid_image_url(url):
            await self.bot.say("**That is not a valid image url!**")  
        else:          
            self.backgrounds["profile"][name] = url
            fileIO('data/leveler/backgrounds.json', "save", self.backgrounds)                          
            await self.bot.say("**New profile background(`{}`) added.**".format(name))

    @checks.admin_or_permissions(manage_server=True)
    @lvladminbg.command(no_pm=True)
    async def addrankbg(self, name:str, url:str):
        """Add a rank background. Proportions: (360px x 100px)"""
        if name in self.backgrounds["rank"].keys():
            await self.bot.say("**That rank background name already exists!**")
        elif not await self._valid_image_url(url):
            await self.bot.say("**That is not a valid image url!**") 
        else:
            self.backgrounds["rank"][name] = url
            fileIO('data/leveler/backgrounds.json', "save", self.backgrounds)
            await self.bot.say("**New rank background(`{}`) added.**".format(name))

    @checks.admin_or_permissions(manage_server=True)
    @lvladminbg.command(no_pm=True)
    async def addlevelbg(self, name:str, url:str):
        '''Add a level-up background. Proportions: (85px x 105px)'''
        if name in self.backgrounds["levelup"].keys():
            await self.bot.say("**That level-up background name already exists!**")
        elif not await self._valid_image_url(url):
            await self.bot.say("**That is not a valid image url!**") 
        else:
            self.backgrounds["levelup"][name] = url
            fileIO('data/leveler/backgrounds.json', "save", self.backgrounds)
            await self.bot.say("**New level-up background(`{}`) added.**".format(name))

    @checks.admin_or_permissions(manage_server=True)
    @lvladminbg.command(no_pm=True)
    async def delprofilebg(self, name:str):
        '''Delete a profile background.'''
        if name in self.backgrounds["profile"].keys():
            del self.backgrounds["profile"][name]
            fileIO('data/leveler/backgrounds.json', "save", self.backgrounds)
            await self.bot.say("**The profile background(`{}`) has been deleted.**".format(name))
        else:                                 
            await self.bot.say("**That profile background name doesn't exist.**")

    @checks.admin_or_permissions(manage_server=True)
    @lvladminbg.command(no_pm=True)
    async def delrankbg(self, name:str):
        '''Delete a rank background.'''
        if name in self.backgrounds["rank"].keys():
            del self.backgrounds["rank"][name]
            fileIO('data/leveler/backgrounds.json', "save", self.backgrounds)
            await self.bot.say("**The rank background(`{}`) has been deleted.**".format(name))
        else:                                 
            await self.bot.say("**That rank background name doesn't exist.**")

    @checks.admin_or_permissions(manage_server=True)
    @lvladminbg.command(no_pm=True)
    async def dellevelbg(self, name:str):
        '''Delete a level background.'''
        if name in self.backgrounds["levelup"].keys():
            del self.backgrounds["levelup"][name]
            fileIO('data/leveler/backgrounds.json', "save", self.backgrounds)
            await self.bot.say("**The level-up background(`{}`) has been deleted.**".format(name))
        else:                                 
            await self.bot.say("**That level-up background name doesn't exist.**")
    
    async def draw_profile(self, user, server):
        name_fnt = ImageFont.truetype(font_bold_file, 22)
        header_u_fnt = ImageFont.truetype(font_unicode_file, 18)
        title_fnt = ImageFont.truetype(font_file, 18)
        sub_header_fnt = ImageFont.truetype(font_bold_file, 14)
        badge_fnt = ImageFont.truetype(font_bold_file, 12)
        exp_fnt = ImageFont.truetype(font_bold_file, 13)
        large_fnt = ImageFont.truetype(font_bold_file, 33)
        level_label_fnt = ImageFont.truetype(font_bold_file, 22)
        general_info_fnt = ImageFont.truetype(font_bold_file, 15)
        general_info_u_fnt = ImageFont.truetype(font_unicode_file, 11)
        rep_fnt = ImageFont.truetype(font_bold_file, 30)
        text_fnt = ImageFont.truetype(font_bold_file, 12)
        text_u_fnt = ImageFont.truetype(font_unicode_file, 8)
        credit_fnt = ImageFont.truetype(font_bold_file, 10)

        def _write_unicode(text, init_x, y, font, unicode_font, fill):
            write_pos = init_x

            for char in text:
                if char.isalnum() or char in string.punctuation or char in string.whitespace:
                    draw.text((write_pos, y), char, font=font, fill=fill)
                    write_pos += font.getsize(char)[0] 
                else:
                    draw.text((write_pos, y), u"{}".format(char), font=unicode_font, fill=fill)
                    write_pos += unicode_font.getsize(char)[0]

        # get urls
        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")
        bg_url = userinfo["profile_background"]
        profile_url = user.avatar_url 

        # create image objects
        bg_image = Image
        profile_image = Image   
    
        async with aiohttp.get(bg_url) as r:
            image = await r.content.read()
        with open('data/leveler/users/{}/temp_profile_bg.png'.format(user.id),'wb') as f:
            f.write(image)
        try:
            async with aiohttp.get(profile_url) as r:
                image = await r.content.read()
        except:
            async with aiohttp.get(default_avatar_url) as r:
                image = await r.content.read()
        with open('data/leveler/users/{}/temp_profile_profile.png'.format(user.id),'wb') as f:
            f.write(image)

        bg_image = Image.open('data/leveler/users/{}/temp_profile_bg.png'.format(user.id)).convert('RGBA')            
        profile_image = Image.open('data/leveler/users/{}/temp_profile_profile.png'.format(user.id)).convert('RGBA')

        # set canvas
        bg_color = (255,255,255,0)
        result = Image.new('RGBA', (290, 290), bg_color)
        process = Image.new('RGBA', (290, 290), bg_color)

        # draw
        draw = ImageDraw.Draw(process)

        # puts in background
        bg_image = bg_image.resize((290, 290), Image.ANTIALIAS)
        bg_image = bg_image.crop((0,0, 290, 290))
        result.paste(bg_image, (0,0))

        # draw filter
        draw.rectangle([(0,0),(290, 290)], fill=(0,0,0,10))

        # draw transparent overlay
        vert_pos = 110
        left_pos = 70
        right_pos = 285
        title_height = 22
        gap = 3

        # determines rep section color
        if "rep_color" not in userinfo.keys() or not userinfo["rep_color"]:
            rep_fill = (92,130,203,230)
        else:
            rep_fill = tuple(userinfo["rep_color"])
        # determines badge section color, should be behind the titlebar
        if "badge_col_color" not in userinfo.keys() or not userinfo["badge_col_color"]:
            badge_fill = (128,151,165,230)
        else:
            badge_fill = tuple(userinfo["badge_col_color"])

        draw.rectangle([(left_pos - 20, vert_pos + title_height), (right_pos, 156)], fill=(40,40,40,230)) # title box
        draw.rectangle([(100,159), (285, 212)], fill=(30, 30 ,30, 220)) # general content
        draw.rectangle([(100,215), (285, 285)], fill=(30, 30 ,30, 220)) # info content

        # stick in credits if needed
        if bg_url in bg_credits.keys():
            credit_text = "  ".join("Background by {}".format(bg_credits[bg_url]))
            credit_init = 290 - credit_fnt.getsize(credit_text)[0]
            draw.text((credit_init, 0), credit_text,  font=credit_fnt, fill=(0,0,0,100))
        draw.rectangle([(5, vert_pos), (right_pos, vert_pos + title_height)], fill=(230,230,230,230)) # name box in front

        # draw level circle
        multiplier = 8
        lvl_circle_dia = 104
        circle_left = 1
        circle_top = 42
        raw_length = lvl_circle_dia * multiplier

        # create mask
        mask = Image.new('L', (raw_length, raw_length), 0)
        draw_thumb = ImageDraw.Draw(mask)
        draw_thumb.ellipse((0, 0) + (raw_length, raw_length), fill = 255, outline = 0)

        # drawing level bar calculate angle
        start_angle = -90 # from top instead of 3oclock
        angle = int(360 * (userinfo["servers"][server.id]["current_exp"]/self._required_exp(userinfo["servers"][server.id]["level"]))) + start_angle

        # level outline
        lvl_circle = Image.new("RGBA", (raw_length, raw_length))
        draw_lvl_circle = ImageDraw.Draw(lvl_circle)
        draw_lvl_circle.ellipse([0, 0, raw_length, raw_length], fill=(badge_fill[0], badge_fill[1], badge_fill[2], 180), outline = (255, 255, 255, 250))
        # determines exp bar color
        if "profile_exp_color" not in userinfo.keys() or not userinfo["profile_exp_color"]:
            exp_fill = (255, 255, 255, 230)
        else:
            exp_fill = tuple(userinfo["profile_exp_color"])
        draw_lvl_circle.pieslice([0, 0, raw_length, raw_length], start_angle, angle, fill=exp_fill, outline = (255, 255, 255, 255))
        # put on level bar circle
        lvl_circle = lvl_circle.resize((lvl_circle_dia, lvl_circle_dia), Image.ANTIALIAS)
        lvl_bar_mask = mask.resize((lvl_circle_dia, lvl_circle_dia), Image.ANTIALIAS)
        process.paste(lvl_circle, (circle_left, circle_top), lvl_bar_mask)  

        # draws boxes
        draw.rectangle([(5,133), (100, 285)], fill= badge_fill) # badges
        draw.rectangle([(10,138), (95, 168)], fill = rep_fill) # reps

        total_gap = 10
        border = int(total_gap/2)
        profile_size = lvl_circle_dia - total_gap
        raw_length = profile_size * multiplier
        # put in profile picture
        output = ImageOps.fit(profile_image, (raw_length, raw_length), centering=(0.5, 0.5))
        output = output.resize((profile_size, profile_size), Image.ANTIALIAS)
        mask = mask.resize((profile_size, profile_size), Image.ANTIALIAS)      
        profile_image = profile_image.resize((profile_size, profile_size), Image.ANTIALIAS)
        process.paste(profile_image, (circle_left + border, circle_top + border), mask)
        
        # write label text
        white_color = (240,240,240,255)
        light_color = (160,160,160,255)

        head_align = 105
        _write_unicode(self._truncate_text(self._name(user, 24), 24), head_align, vert_pos + 3, level_label_fnt, header_u_fnt, (110,110,110,255)) # NAME
        _write_unicode(userinfo["title"], head_align, 136, level_label_fnt, header_u_fnt, white_color)

        # draw level box
        level_right = 290
        level_left = level_right - 72
        draw.rectangle([(level_left, 0), (level_right, 21)], fill=(rep_fill[0],rep_fill[1],rep_fill[2],160)) # box
        lvl_text = "LEVEL {}".format(userinfo["servers"][server.id]["level"])
        if badge_fill == (128,151,165,230):
            lvl_color = white_color
        else:
            lvl_color = self._contrast(rep_fill, badge_fill)   
        draw.text((self._center(level_left, level_right, lvl_text, level_label_fnt), 2), lvl_text,  font=level_label_fnt, fill=(lvl_color[0],lvl_color[1],lvl_color[2],255)) # Level #

        rep_text = "+{} rep".format(userinfo["rep"])
        draw.text((self._center(5, 100, rep_text, rep_fnt), 141), rep_text, font=rep_fnt, fill=white_color)

        draw.text((self._center(5, 100, "Badges", sub_header_fnt), 173), "Badges", font=sub_header_fnt, fill=white_color) # Badges   

        exp_text = "{}/{}".format(userinfo["servers"][server.id]["current_exp"],self._required_exp(userinfo["servers"][server.id]["level"])) # Exp
        exp_color = self._contrast(badge_fill, exp_fill)
        draw.text((105, 99), exp_text,  font=exp_fnt, fill=(exp_color[0], exp_color[1], exp_color[2], 255)) # Exp Text
        
        lvl_left = 100
        label_align = 105
        _write_unicode(u"Rank:", label_align, 165, general_info_fnt, general_info_u_fnt, light_color)
        draw.text((label_align, 180), "Exp:",  font=general_info_fnt, fill=light_color) # Exp
        draw.text((label_align, 195), "Towels:",  font=general_info_fnt, fill=light_color) # Credits

        # local stats
        num_local_align = 180
        local_symbol = u"\U0001F3E0 "
        if "linux" in platform.system().lower():
            local_symbol = u"\U0001F3E0 "
        else:
            local_symbol = "S "

        s_rank_txt = local_symbol + self._truncate_text("#{}".format(await self._find_server_rank(user, server)), 8)
        _write_unicode(s_rank_txt, num_local_align - general_info_u_fnt.getsize(local_symbol)[0], 165, general_info_fnt, general_info_u_fnt, light_color) # Rank 

        s_exp_txt = self._truncate_text("{}".format(await self._find_server_exp(user, server)), 8)
        _write_unicode(s_exp_txt, num_local_align, 180, general_info_fnt, general_info_u_fnt, light_color)  # Exp
        try:
            bank = self.bot.get_cog('Economy').bank
            if bank.account_exists(user):
                credits = bank.get_balance(user)
            else:
                credits = 0
        except:
            credits = 0
        credit_txt = "${}".format(credits)
        draw.text((num_local_align, 195), self._truncate_text(credit_txt, 18),  font=general_info_fnt, fill=light_color) # Credits

        # global stats
        num_align = 230
        if "linux" in platform.system().lower():
            global_symbol = u"\U0001F30E "
            fine_adjust = 1
        else:
            global_symbol = "G "
            fine_adjust = 0

        rank_txt = global_symbol + self._truncate_text("#{}".format(await self._find_global_rank(user, server)), 8)
        exp_txt = self._truncate_text("{}".format(userinfo["total_exp"]), 8)
        _write_unicode(rank_txt, num_align - general_info_u_fnt.getsize(global_symbol)[0] + fine_adjust, 165, general_info_fnt, general_info_u_fnt, light_color) # Rank 
        _write_unicode(exp_txt, num_align, 180, general_info_fnt, general_info_u_fnt, light_color)  # Exp

        draw.text((105, 220), "Info Box",  font=sub_header_fnt, fill=white_color) # Info Box 
        margin = 105
        offset = 238
        for line in textwrap.wrap(userinfo["info"], width=40):
            # draw.text((margin, offset), line, font=text_fnt, fill=(70,70,70,255))
            _write_unicode(line, margin, offset, text_fnt, text_u_fnt, light_color)            
            offset += text_fnt.getsize(line)[1] + 2

        # sort badges
        priority_badges = []
        for badge in userinfo["badges"]:
            priority_num = self.badges[badge]["priority_num"]
            priority_badges.append((badge, priority_num))
        sorted_badges = sorted(priority_badges, key=operator.itemgetter(1), reverse=True)

        # TODO: simplify this. it shouldn't be this complicated... sacrifice conciseness for customizability
        if "badge_type" not in self.settings.keys() or self.settings["badge_type"] == "circles":
            # circles require antialiasing
            vert_pos = 187
            right_shift = 6
            left = 10 + right_shift
            right = 52 + right_shift
            coord = [(left, vert_pos), (right, vert_pos), (left, vert_pos + 33), (right, vert_pos + 33), (left, vert_pos + 66), (right, vert_pos + 66)]
            i = 0
            total_gap = 2 # /2
            border_width = int(total_gap/2)

            for pair in sorted_badges[:6]:
                badge = pair[0]
                bg_color = self.badges[badge]["bg_color"]
                text_color = self.badges[badge]["text_color"]
                border_color = self.badges[badge]["border_color"]
                text = badge.replace("_", " ")
                size = 32
                multiplier = 6 # for antialiasing
                raw_length = size * multiplier

                # draw mask circle
                mask = Image.new('L', (raw_length, raw_length), 0)
                draw_thumb = ImageDraw.Draw(mask)
                draw_thumb.ellipse((0, 0) + (raw_length, raw_length), fill = 255, outline = 0)

                # determine image or color for badge bg
                if await self._valid_image_url(bg_color):
                    # get image
                    async with aiohttp.get(bg_color) as r:
                        image = await r.content.read()
                    with open('data/leveler/users/{}/temp_badge.png'.format(user.id),'wb') as f:
                        f.write(image)
                    badge_image = Image.open('data/leveler/users/{}/temp_badge.png'.format(user.id)).convert('RGBA')
                    badge_image = badge_image.resize((raw_length, raw_length), Image.ANTIALIAS)

                    # structured like this because if border = 0, still leaves outline.
                    if border_color:
                        square = Image.new('RGBA', (raw_length, raw_length), border_color)
                        # put border on ellipse/circle
                        output = ImageOps.fit(square, (raw_length, raw_length), centering=(0.5, 0.5))
                        output = output.resize((size, size), Image.ANTIALIAS)
                        outer_mask = mask.resize((size, size), Image.ANTIALIAS)
                        process.paste(output, coord[i], outer_mask)

                        # put on ellipse/circle
                        output = ImageOps.fit(badge_image, (raw_length, raw_length), centering=(0.5, 0.5))
                        output = output.resize((size - total_gap, size - total_gap), Image.ANTIALIAS)
                        inner_mask = mask.resize((size - total_gap, size - total_gap), Image.ANTIALIAS)
                        process.paste(output, (coord[i][0] + border_width, coord[i][1] + border_width), inner_mask)
                    else:
                        # put on ellipse/circle
                        output = ImageOps.fit(badge_image, (raw_length, raw_length), centering=(0.5, 0.5))
                        output = output.resize((size, size), Image.ANTIALIAS)
                        outer_mask = mask.resize((size, size), Image.ANTIALIAS)
                        process.paste(output, coord[i], outer_mask)
                    os.remove('data/leveler/users/{}/temp_badge.png'.format(user.id))
                else: # if it's just a color
                    if border_color:
                        # border
                        square = Image.new('RGBA', (raw_length, raw_length), border_color)
                        output = ImageOps.fit(square, (raw_length, raw_length), centering=(0.5, 0.5))
                        output = output.resize((size, size), Image.ANTIALIAS)
                        outer_mask = mask.resize((size, size), Image.ANTIALIAS)
                        process.paste(output, coord[i], outer_mask)

                        # put on ellipse/circle
                        square = Image.new('RGBA', (raw_length, raw_length), bg_color)
                        output = ImageOps.fit(square, (raw_length, raw_length), centering=(0.5, 0.5))
                        output = output.resize((size - total_gap, size - total_gap), Image.ANTIALIAS)
                        inner_mask = mask.resize((size - total_gap, size - total_gap), Image.ANTIALIAS)
                        process.paste(output, (coord[i][0] + border_width, coord[i][1] + border_width), inner_mask)
                        draw.text((self._center(coord[i][0], coord[i][0] + size, badge[:6], badge_fnt), coord[i][1] + 12), badge[:6],  font=badge_fnt, fill=text_color) # Text
                    else:
                        square = Image.new('RGBA', (raw_length, raw_length), bg_color)
                        output = ImageOps.fit(square, (raw_length, raw_length), centering=(0.5, 0.5))
                        output = output.resize((size, size), Image.ANTIALIAS)
                        outer_mask = mask.resize((size, size), Image.ANTIALIAS)
                        process.paste(output, coord[i], outer_mask)
                        draw.text((self._center(coord[i][0], coord[i][0] + size, badge[:6], badge_fnt), coord[i][1] + 12), badge[:6],  font=badge_fnt, fill=text_color) # Text
                i += 1
        elif self.settings["badge_type"] == "squares":
            # squares, cause eslyium.
            vert_pos = 188
            right_shift = 6
            left = 10 + right_shift
            right = 52 + right_shift
            coord = [(left, vert_pos), (right, vert_pos), (left, vert_pos + 33), (right, vert_pos + 33), (left, vert_pos + 66), (right, vert_pos + 66)]
            total_gap = 4
            border_width = int(total_gap/2)
            i = 0
            for pair in sorted_badges[:6]:
                badge = pair[0]
                bg_color = self.badges[badge]["bg_color"]
                text_color = self.badges[badge]["text_color"]
                border_color = self.badges[badge]["border_color"]
                text = badge.replace("_", " ")
                size = 32

                # determine image or color for badge bg, this is also pretty terrible tbh...
                if await self._valid_image_url(bg_color):
                    # get image
                    async with aiohttp.get(bg_color) as r:
                        image = await r.content.read()
                    with open('data/leveler/users/{}/temp_badge.png'.format(user.id),'wb') as f:
                        f.write(image)

                    badge_image = Image.open('data/leveler/users/{}/temp_badge.png'.format(user.id)).convert('RGBA')
                    if border_color != None:
                        draw.rectangle([coord[i], (coord[i][0] + size, coord[i][1] + size)], fill=border_color) # border
                        badge_image = badge_image.resize((size - total_gap + 1, size - total_gap + 1), Image.ANTIALIAS)
                        process.paste(badge_image, (coord[i][0] + border_width, coord[i][1] + border_width))
                    else:
                        badge_image = badge_image.resize((size, size), Image.ANTIALIAS)
                        process.paste(badge_image, coord[i])
                    os.remove('data/leveler/users/{}/temp_badge.png'.format(user.id))
                else:
                    if border_color != None:
                        draw.rectangle([coord[i], (coord[i][0] + size, coord[i][1] + size)], fill=border_color) # border
                        draw.rectangle([(coord[i][0] + border_width, coord[i][1] + border_width), (coord[i][0] + size - border_width, coord[i][1] + size - border_width)], fill=bg_color) # bg               
                    else:
                        draw.rectangle([coord[i], (coord[i][0] + size, coord[i][1] + size)], fill = bg_color)
                    draw.text((self._center(coord[i][0], coord[i][0] + size, badge[:6], badge_fnt), coord[i][1] + 12), badge[:6],  font=badge_fnt, fill=text_color) # Text            
                i+=1
        elif self.settings["badge_type"] == "tags" or self.settings["badge_type"] == "bars":
            vert_pos = 190
            i = 0
            for pair in sorted_badges[:5]:
                badge = pair[0]
                bg_color = self.badges[badge]["bg_color"]
                text_color = self.badges[badge]["text_color"]
                border_color = self.badges[badge]["border_color"]
                left_pos = 10
                right_pos = 95
                text = badge.replace("_", " ")
                total_gap = 4
                border_width = int(total_gap/2)
                bar_size = (85, 15)

                # determine image or color for badge bg
                if await self._valid_image_url(bg_color):
                    async with aiohttp.get(bg_color) as r:
                        image = await r.content.read()
                    with open('data/leveler/users/{}/temp_badge.png'.format(user.id),'wb') as f:
                        f.write(image)
                    badge_image = Image.open('data/leveler/users/{}/temp_badge.png'.format(user.id)).convert('RGBA')

                    if border_color != None:
                        draw.rectangle([(left_pos, vert_pos + i*17), (right_pos, vert_pos + 15 + i*17)], fill = border_color, outline = border_color) # border
                        badge_image = badge_image.resize((bar_size[0] - total_gap + 1, bar_size[1] - total_gap + 1), Image.ANTIALIAS)
                        process.paste(badge_image, (left_pos + border_width, vert_pos + border_width + i*17))
                    else:
                        badge_image = badge_image.resize(bar_size, Image.ANTIALIAS)
                        process.paste(badge_image, (left_pos,vert_pos + i*17))                    
                    os.remove('data/leveler/users/{}/temp_badge.png'.format(user.id))
                else:
                    if border_color != None:
                        draw.rectangle([(left_pos, vert_pos + i*17), (right_pos, vert_pos + 15 + i*17)], fill = border_color, outline = border_color) # border
                        draw.rectangle([(left_pos + border_width, vert_pos + border_width + i*17), (right_pos - border_width, vert_pos - border_width + 15 + i*17)], fill = bg_color) # bg                       
                    else:
                        draw.rectangle([(left_pos,vert_pos + i*17), (right_pos, vert_pos + 15 + i*17)], fill = bg_color, outline = border_color) # bg
                    bar_fnt = ImageFont.truetype(font_bold_file, 14) # a slightly bigger font was requested
                    draw.text((self._center(left_pos,right_pos, text, bar_fnt), vert_pos + 2 + i*17), text,  font=bar_fnt, fill = text_color) # Credits
                vert_pos += 2 # spacing
                i += 1

        result = Image.alpha_composite(result, process)
        result.save('data/leveler/users/{}/profile.png'.format(user.id),'PNG', quality=100)

    # returns new text color based on the bg. doesn't work great.
    def _contrast(self, bg_color, text_color):
        min_diff = .50 # percent difference
        dr = (bg_color[0] - text_color[0])
        dg = (bg_color[1] - text_color[1])
        db = (bg_color[2] - text_color[2])

        if bg_color[0] != 0:
            dr /= bg_color[0]
        if bg_color[1] != 0:
            dr /= bg_color[1]
        if bg_color[2] != 0:
            dr /= bg_color[2]

        if abs(dr) > min_diff or abs(dg) > min_diff or abs(dg) > min_diff:
            return text_color
        else:
            new_color = []
            if dr > 0 or dg > 0 or db > 0:
                for val in bg_color:
                    new_color.append(int(val*min_diff))
                return tuple(new_color)
            else:
                for val in bg_color:
                    val = val*(1+min_diff)
                    if val > 255:
                        val = 255
                    new_color.append(int(val))
                return tuple(new_color)

    def _luminance(self, color):
        return (0.2126*color[0]) + (0.7152*color[1]) + (0.0722*color[2])

    # returns a string with possibly a nickname
    def _name(self, user, max_length):
        if user.name == user.display_name:
            return user.name
        else:
            return "{} ({})".format(user.name, self._truncate_text(user.display_name, max_length - len(user.name) - 3), max_length)

    async def draw_rank(self, user, server):

        # fonts
        name_fnt = ImageFont.truetype(font_bold_file, 22)
        header_u_fnt = ImageFont.truetype(font_unicode_file, 18)
        sub_header_fnt = ImageFont.truetype(font_bold_file, 14)
        badge_fnt = ImageFont.truetype(font_bold_file, 12)
        large_fnt = ImageFont.truetype(font_bold_file, 33)
        level_label_fnt = ImageFont.truetype(font_bold_file, 22)
        general_info_fnt = ImageFont.truetype(font_bold_file, 15)
        general_info_u_fnt = ImageFont.truetype(font_unicode_file, 11)
        credit_fnt = ImageFont.truetype(font_bold_file, 10)

        def _write_unicode(text, init_x, y, font, unicode_font, fill):
            write_pos = init_x

            for char in text:
                if char.isalnum() or char in string.punctuation or char in string.whitespace:
                    draw.text((write_pos, y), char, font=font, fill=fill)
                    write_pos += font.getsize(char)[0] 
                else:
                    draw.text((write_pos, y), u"{}".format(char), font=unicode_font, fill=fill)
                    write_pos += unicode_font.getsize(char)[0]

        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")
        # get urls
        bg_url = userinfo["rank_background"]
        profile_url = user.avatar_url         

        # create image objects
        bg_image = Image
        profile_image = Image      
    
        async with aiohttp.get(bg_url) as r:
            image = await r.content.read()
        with open('data/leveler/users/{}/temp_rank_bg.png'.format(user.id),'wb') as f:
            f.write(image)
        try:
            async with aiohttp.get(profile_url) as r:
                image = await r.content.read()
        except:
            async with aiohttp.get(default_avatar_url) as r:
                image = await r.content.read()
        with open('data/leveler/users/{}/temp_rank_profile.png'.format(user.id),'wb') as f:
            f.write(image)

        bg_image = Image.open('data/leveler/users/{}/temp_rank_bg.png'.format(user.id)).convert('RGBA')            
        profile_image = Image.open('data/leveler/users/{}/temp_rank_profile.png'.format(user.id)).convert('RGBA')

        # set canvas
        bg_color = (255,255,255, 0)
        result = Image.new('RGBA', (360, 100), bg_color)
        process = Image.new('RGBA', (360, 100), bg_color)
        
        # puts in background
        bg_image = bg_image.resize((360, 100), Image.ANTIALIAS)
        bg_image = bg_image.crop((0,0, 360, 100))
        result.paste(bg_image, (0,0))

        # draw
        draw = ImageDraw.Draw(process)

        # draw transparent overlay
        vert_pos = 5
        left_pos = 70
        right_pos = 360 - vert_pos
        title_height = 22
        gap = 3

        draw.rectangle([(left_pos - 20,vert_pos), (right_pos, vert_pos + title_height)], fill=(230,230,230,230)) # title box
        content_top = vert_pos + title_height + gap
        content_bottom = 100 - vert_pos
        draw.rectangle([(left_pos - 20, content_top), (right_pos, content_bottom)], fill=(30, 30 ,30, 220), outline=(230,230,230,230)) # content box

        # stick in credits if needed
        if bg_url in bg_credits.keys():
            credit_text = " ".join("{}".format(bg_credits[bg_url]))
            draw.text((2, 92), credit_text,  font=credit_fnt, fill=(0,0,0,190))

        # draw level circle
        multiplier = 6  
        lvl_circle_dia = 94
        circle_left = 15
        circle_top = int((100 - lvl_circle_dia)/2)
        raw_length = lvl_circle_dia * multiplier

        # create mask
        mask = Image.new('L', (raw_length, raw_length), 0)
        draw_thumb = ImageDraw.Draw(mask)
        draw_thumb.ellipse((0, 0) + (raw_length, raw_length), fill = 255, outline = 0)

        # drawing level bar calculate angle
        start_angle = -90 # from top instead of 3oclock
        angle = int(360 * (userinfo["servers"][server.id]["current_exp"]/self._required_exp(userinfo["servers"][server.id]["level"]))) + start_angle
     
        lvl_circle = Image.new("RGBA", (raw_length, raw_length))
        draw_lvl_circle = ImageDraw.Draw(lvl_circle)
        draw_lvl_circle.ellipse([0, 0, raw_length, raw_length], fill=(180, 180, 180, 180), outline = (255, 255, 255, 220))
        # determines exp bar color
        if "rank_exp_color" not in userinfo.keys() or not userinfo["rank_exp_color"]:
            exp_fill = (255, 255, 255, 230)
        else:
            exp_fill = tuple(userinfo["rank_exp_color"])
        draw_lvl_circle.pieslice([0, 0, raw_length, raw_length], start_angle, angle, fill=exp_fill, outline = (255, 255, 255, 230))
        # put on level bar circle
        lvl_circle = lvl_circle.resize((lvl_circle_dia, lvl_circle_dia), Image.ANTIALIAS)
        lvl_bar_mask = mask.resize((lvl_circle_dia, lvl_circle_dia), Image.ANTIALIAS)
        process.paste(lvl_circle, (circle_left, circle_top), lvl_bar_mask)       

        # draws mask
        total_gap = 10
        border = int(total_gap/2)
        profile_size = lvl_circle_dia - total_gap
        raw_length = profile_size * multiplier
        # put in profile picture
        output = ImageOps.fit(profile_image, (raw_length, raw_length), centering=(0.5, 0.5))
        output = output.resize((profile_size, profile_size), Image.ANTIALIAS)
        mask = mask.resize((profile_size, profile_size), Image.ANTIALIAS)      
        profile_image = profile_image.resize((profile_size, profile_size), Image.ANTIALIAS)
        process.paste(profile_image, (circle_left + border, circle_top + border), mask)
        
        # draw level box
        level_left = 277
        level_right = right_pos
        draw.rectangle([(level_left, vert_pos), (level_right, vert_pos + title_height)], fill="#AAA") # box
        lvl_text = "LEVEL {}".format(userinfo["servers"][server.id]["level"])     
        draw.text((self._center(level_left, level_right, lvl_text, level_label_fnt), vert_pos + 2), lvl_text,  font=level_label_fnt, fill=(110,110,110,255)) # Level #

        # draw text
        grey_color = (110,110,110,255)
        white_color = (230,230,230,255)
        # reputation points
        left_text_align = 130
        rep_align = self._center(110, 190, "R e p s", level_label_fnt)
        _write_unicode(self._truncate_text(self._name(user, 21), 21), left_text_align - 20, vert_pos + 2, name_fnt, header_u_fnt, grey_color) # Name 
        draw.text((rep_align, 37), "R e p s".format(await self._find_server_rank(user, server)), font=level_label_fnt, fill=white_color) # Rep Label
        rep_label_width = level_label_fnt.getsize("Reps")[0]
        rep_text = "+{}".format(userinfo["rep"])
        draw.text((self._center(rep_align, rep_align + rep_label_width, rep_text, large_fnt) , 63), rep_text, font=large_fnt, fill=white_color) # Rep
       
        # divider bar
        draw.rectangle([(190, 45), (191, 85)], fill=(160,160,160,240))      

        # labels
        label_align = 210
        draw.text((label_align, 38), "Server Rank:", font=general_info_fnt, fill=white_color) # Server Rank
        draw.text((label_align, 58), "Server Exp:", font=general_info_fnt, fill=white_color) # Server Exp
        draw.text((label_align, 78), "Towels:", font=general_info_fnt, fill=white_color) # Credit
        # info
        right_text_align = 290
        rank_txt = "#{}".format(await self._find_server_rank(user, server))
        draw.text((right_text_align, 38), self._truncate_text(rank_txt, 12) , font=general_info_fnt, fill=white_color) # Rank
        exp_txt = "{}".format(await self._find_server_exp(user, server))
        draw.text((right_text_align, 58), self._truncate_text(exp_txt, 12), font=general_info_fnt, fill=white_color) # Exp
        try:
            bank = self.bot.get_cog('Economy').bank
            if bank.account_exists(user):
                credits = bank.get_balance(user)
            else:
                credits = 0
        except:
            credits = 0
        credit_txt = "${}".format(credits)
        draw.text((right_text_align, 78), self._truncate_text(credit_txt, 12),  font=general_info_fnt, fill=white_color) # Credits

        result = Image.alpha_composite(result, process)
        result.save('data/leveler/users/{}/rank.png'.format(user.id),'PNG', quality=100)

    async def draw_levelup(self, user, server):
        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")
        # get urls
        bg_url = userinfo["levelup_background"]
        profile_url = user.avatar_url         

        # create image objects
        bg_image = Image
        profile_image = Image   
    
        async with aiohttp.get(bg_url) as r:
            image = await r.content.read()
        with open('data/leveler/users/{}/temp_level_bg.png'.format(user.id),'wb') as f:
            f.write(image)
        try:
            async with aiohttp.get(profile_url) as r:
                image = await r.content.read()
        except:
            async with aiohttp.get(default_avatar_url) as r:
                image = await r.content.read()
        with open('data/leveler/users/{}/temp_level_profile.png'.format(user.id),'wb') as f:
            f.write(image)

        bg_image = Image.open('data/leveler/users/{}/temp_level_bg.png'.format(user.id)).convert('RGBA')            
        profile_image = Image.open('data/leveler/users/{}/temp_level_profile.png'.format(user.id)).convert('RGBA')

        # set canvas
        bg_color = (255,255,255, 0)
        result = Image.new('RGBA', (85, 105), bg_color)
        process = Image.new('RGBA', (85, 105), bg_color)

        # draw
        draw = ImageDraw.Draw(process)

        # puts in background
        bg_image = bg_image.resize((85, 105), Image.ANTIALIAS)
        bg_image = bg_image.crop((0,0, 85, 105))
        result.paste(bg_image, (0,0))

        # draw transparent overlay   
        draw.rectangle([(0, 40), (85, 105)], fill=(30, 30 ,30, 220)) # white portion
        draw.rectangle([(15, 11), (68, 64)], fill=(255,255,255,160), outline=(100, 100, 100, 100)) # profile rectangle

        # put in profile picture
        profile_size = (50, 50)
        profile_image = profile_image.resize(profile_size, Image.ANTIALIAS)
        process.paste(profile_image, (17, 13))

        # fonts
        level_fnt2 = ImageFont.truetype('data/leveler/fonts/font_bold.ttf', 20)
        level_fnt = ImageFont.truetype('data/leveler/fonts/font_bold.ttf', 32)

        # write label text
        draw.text((self._center(0, 85, "Level Up!", level_fnt2), 65), "Level Up!", font=level_fnt2, fill=(240,240,240,255)) # Level
        lvl_text = "LVL {}".format(userinfo["servers"][server.id]["level"])
        draw.text((self._center(0, 85, lvl_text, level_fnt), 80), lvl_text, font=level_fnt, fill=(240,240,240,255)) # Level Number

        result = Image.alpha_composite(result, process)
        result.save('data/leveler/users/{}/level.png'.format(user.id),'PNG', quality=100)

    # loads the new text into the model
    async def on_message(self, message): 
        await self._handle_on_message(message)

    async def _handle_on_message(self, message):
        text = message.content
        channel = message.channel
        server = message.author.server
        user = message.author
        # creates user if doesn't exist, bots are not logged.
        await self._create_user(user, server)
        curr_time = time.time()
        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")

        if server.id in self.settings["disabled_servers"]:
            return
        if user.bot:
            return

        # check if chat_block exists
        if "chat_block" not in userinfo:
            userinfo["chat_block"] = 0

        if float(curr_time) - float(userinfo["chat_block"]) >= 120 and not any(text.startswith(x) for x in prefix):
            await self._process_exp(message, userinfo, random.randint(15, 20))

    async def _process_exp(self, message, userinfo, exp:int):
        server = message.author.server
        channel = message.channel
        user = message.author

        # add to total exp
        required = self._required_exp(userinfo["servers"][server.id]["level"])
        userinfo["total_exp"] += exp
        if userinfo["servers"][server.id]["current_exp"] + exp >= required:
            print ("LEVEL UP TRIGGERED")
            userinfo["servers"][server.id]["level"] += 1
            userinfo["servers"][server.id]["current_exp"] = userinfo["servers"][server.id]["current_exp"] + exp - required
            userinfo["chat_block"] = time.time()
            fileIO("data/leveler/users/{}/info.json".format(user.id), "save", userinfo)
         
            if not isinstance(self.settings["lvl_msg"], list):
                self.settings["lvl_msg"] = []

            print(server.id in self.settings["lvl_msg"])

            if server.id in self.settings["lvl_msg"]: # if lvl msg is enabled
                print("3") 
                # channel lock implementation
                if "lvl_msg_lock" in self.settings.keys() and server.id in self.settings["lvl_msg_lock"].keys():
                    channel_id = self.settings["lvl_msg_lock"][server.id]
                    channel = find(lambda m: m.id == channel_id, server.channels)

                server_identifier = "" # super hacky
                name = self._is_mention(user) # also super hacky
                # private message takes precedent, of course
                if "private_lvl_msg" in self.settings and server.id in self.settings["private_lvl_msg"]:
                    server_identifier = " on {}".format(server.name)
                    channel = user
                    name = "You"

                print("Level Up")
                if "text_only" in self.settings and server.id in self.settings["text_only"]:
                    await self.bot.send_typing(channel)
                    em = discord.Embed(description='**{} just gained a level{}! (LEVEL {})**'.format(name, server_identifier, userinfo["servers"][server.id]["level"]), colour=user.colour)
                    await self.bot.send_message(channel, '', embed = em)
                else:
                    print("DRAW Level Up")
                    await self.draw_levelup(user, server)
                    await self.bot.send_typing(channel)   
                    await self.bot.send_file(channel, 'data/leveler/users/{}/level.png'.format(user.id), content='**{} just gained a level{}!**'.format(name, server_identifier))
        else:
            userinfo["chat_block"] = time.time()
            userinfo["servers"][server.id]["current_exp"] += exp
            fileIO("data/leveler/users/{}/info.json".format(user.id), "save", userinfo)
        fileIO('data/leveler/settings.json', "save", self.settings)

    async def _find_server_rank(self, user, server):
        targetid = user.id
        users = []
        for userid in os.listdir(user_directory):
            userinfo = fileIO("data/leveler/users/{}/info.json".format(userid), "load")
            if "servers" in userinfo and server.id in userinfo["servers"]:
                temp_user = find(lambda m: m.id == userid, server.members)
                server_exp = 0
                for i in range(userinfo["servers"][server.id]["level"]):
                    server_exp += self._required_exp(i)
                server_exp += userinfo["servers"][server.id]["current_exp"]
                if temp_user != None:
                    users.append((userid, temp_user.name, server_exp))
        sorted_list = sorted(users, key=operator.itemgetter(2), reverse=True)

        rank = 1
        for user in sorted_list:
            if user[0] == targetid:
                return rank
            rank+=1

    async def _find_server_exp(self, user, server):
        server_exp = 0
        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")

        try:
            for i in range(userinfo["servers"][server.id]["level"]):
                server_exp += self._required_exp(i)
            server_exp +=  userinfo["servers"][server.id]["current_exp"]
            return server_exp
        except:
            return server_exp

    async def _find_global_rank(self, user, server):
        users = []
        # this is also terrible...
        for userid in os.listdir(user_directory):
            userinfo = fileIO("data/leveler/users/{}/info.json".format(userid), "load")
            for server in self.bot.servers:
                temp_user = find(lambda m: m.id == userid, server.members)
                if temp_user != None:
                    break
            if temp_user != None:
                users.append((userid, temp_user.name, userinfo["total_exp"]))
        sorted_list = sorted(users, key=operator.itemgetter(2), reverse=True)

        rank = 1
        for stats in sorted_list:
            if stats[0] == user.id:
                return rank
            rank+=1

    # handles user creation, adding new server, blocking
    async def _create_user(self, user, server):
        if not os.path.exists("data/leveler/users/{}".format(user.id)):
            os.makedirs("data/leveler/users/{}".format(user.id))
            new_account = {
                "servers": {},
                "total_exp": 0,
                "profile_background": self.backgrounds["profile"]["default"],
                "rank_background": self.backgrounds["rank"]["default"],
                "levelup_background": self.backgrounds["levelup"]["default"],
                "title": "",
                "info": "I am a mysterious person.",
                "rep": 0,
                "badges":[],
                "rep_color": [],
                "badge_col_color": [],
                "rep_block": 0,
                "chat_block": 0,
                "profile_block": 0,
                "rank_block": 0
            }
            fileIO("data/leveler/users/{}/info.json".format(user.id), "save", new_account)

        userinfo = fileIO("data/leveler/users/{}/info.json".format(user.id), "load")
        if server.id not in userinfo["servers"]:
            userinfo["servers"][server.id] = {
                "level": 0,
                "current_exp": 0
            }
            fileIO("data/leveler/users/{}/info.json".format(user.id), "save", userinfo)

    def _truncate_text(self, text, max_length):
        if len(text) > max_length:
            if text.strip('$').isdigit():
                text = int(text.strip('$'))
                return "${:.2E}".format(text)
            return text[:max_length-3] + "..."
        return text

    # finds the the pixel to center the text
    def _center(self, start, end, text, font):
        dist = end - start
        width = font.getsize(text)[0]
        start_pos = start + ((dist-width)/2)
        return int(start_pos)

    # calculates required exp for next level
    def _required_exp(self, level:int):
        if level < 0:
            return 0
        return 139*level+65
# ------------------------------ setup ----------------------------------------    
def check_folders():
    if not os.path.exists("data/leveler"):
        print("Creating data/leveler folder...")
        os.makedirs("data/leveler")

    if not os.path.exists("data/leveler/users"):
        print("Creating data/leveler/users folder...")
        os.makedirs("data/leveler/users")
        transfer_info()

def transfer_info():
    users = fileIO("data/leveler/users.json", "load")
    for user_id in users:
        os.makedirs("data/leveler/users/{}".format(user_id))
        # create info.json
        f = "data/leveler/users/{}/info.json".format(user_id)
        if not fileIO(f, "check"):
            fileIO(f, "save", users[user_id])        

def check_files():
    default = {
        "bg_price": 0,
        "lvl_msg": [], # enabled lvl msg servers
        "disabled_servers": [],
        "badge_type": "circles",
        "mention" : True,
        "text_only": []
        }

    settings_path = "data/leveler/settings.json"
    if not os.path.isfile(settings_path):
        print("Creating default leveler settings.json...")
        fileIO(settings_path, "save", default)

    bgs = {
            "profile": {
                "alice": "http://puu.sh/qAoLx/7335f697fb.png",
                "bluestairs": "http://puu.sh/qAqpi/5e64aa6804.png",
                "lamp": "http://puu.sh/qJJIb/05e4e02edd.jpg",
                "coastline": "http://puu.sh/qJJVl/f4bf98d408.jpg",
                "redblack": "http://puu.sh/qI0lQ/3a5e04ff05.jpg",
                "default": "http://puu.sh/qNrD6/ee0ef9462d.jpg",
                "iceberg": "http://puu.sh/qAr6p/1d4e031a9e.png",
                "miraiglasses": "http://puu.sh/qArax/ce8a8bf12e.png",
                "miraikuriyama": "http://puu.sh/qArbY/59b883fe71.png",
                "mountaindawn": "http://puu.sh/qJJLa/568b9a318b.jpg",
                "waterlilies": "http://puu.sh/qJJSL/43b0f852c0.jpg"
            },
            "rank": {
                "aurora" : "http://puu.sh/qJJv4/82aeb6de54.jpg",
                "default" : "http://puu.sh/qJJgx/abeda18e15.jpg",
                "nebula": "http://puu.sh/qJJqh/4a530e48ef.jpg",
                "mountain" : "http://puu.sh/qJvR4/52a5797b4f.jpg"
            },
            "levelup": {
                "default" : "http://puu.sh/qJJjz/27f499f989.jpg",
            },
        }

    bgs_path = "data/leveler/backgrounds.json"
    if not os.path.isfile(bgs_path):
        print("Creating default leveler backgrounds.json...")
        fileIO(bgs_path, "save", bgs)

    f = "data/leveler/badges.json"
    if not fileIO(f, "check"):
        print("Creating badges.json...")
        fileIO(f, "save", {})

def setup(bot):
    check_folders()
    check_files()

    n = Leveler(bot)
    bot.add_listener(n.on_message,"on_message")
    bot.add_cog(n)