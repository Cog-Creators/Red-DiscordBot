import discord
from discord.ext import commands
from .utils.dataIO import fileIO
from .utils import checks
from random import choice as randchoice
import asyncio
import os
import sys
import readline
import time
try:
    import msvcrt
except:
    print("Can't import msvcrt. Probably not on Windows")
try:
    import select
    import tty
    import termios
except:
    print("Couldn't import select, tty, and termios. Probably not on Linux")
import threading


class Consoletalk:
    """talk using the bot through a file"""

    def __init__(self,bot):
        self.bot = bot
        self.settings = fileIO("data/consoletalk/settings.json", "load")
        self.above_channel = None
        self.channel = None
        self.is_on_windows = None
        self.queue = asyncio.Queue(1)
        self.waiting_input = False
        self.input_msg = None
        self.self_msg = None
        self.input_thread = None
        self.flush_time = None

    async def print_to_console(self,message):
        if not self.settings["PRINT"]:
            return
        #fix
        try:
            msgid = message.server.id + message.channel.id + message.author.id + message.content
            if self.self_msg != None and msgid == self.self_msg:
                self.self_msg = None
                return
        except:
            pass

        msg = ""
        try:
            msg += message.server.name
            msg += " #"+message.channel.name
            self.above_channel = message.channel.id
        except Exception as e:
            print("--Error in Consoletalk:--")
            print(e)
            print(dir(message))
        msg += "| " + message.author.name + ": " + message.clean_content
        print(msg)


    #code adapted from http://stackoverflow.com/questions/2408560/python-nonblocking-console-input
    def isData(self):
        return select.select([sys.stdin], [], [], 0) == ([sys.stdin], [], [])

    #look at red#owner for threaded approach

    async def input_loop(self, ctx):
        #async method
        if self.is_on_windows == None:
            self.is_on_windows = sys.platform == 'win32'
        while self.settings["INPUT"] and self.getting_input():
            #to_send = input(">")
            #await self.bot.send_message(self.bot.get_channel(self.channel),to_send)
            print("getting more input")
            await asyncio.sleep(.2)
        #code adapted from http://stackoverflow.com/questions/2408560/python-nonblocking-console-input

            if self.is_on_windows == True:
                num = 0
                done = False
                while not done:
                    print(num)
                    num += 1

                    if msvcrt.kbhit():
                        print("you pressed",msvcrt.getch(),"so now i will quit")
                        done = True
            else:
                old_settings = termios.tcgetattr(sys.stdin)
                try:
                    tty.setcbreak(sys.stdin.fileno())

                    line = ""
                    while 1:
                        await asyncio.sleep(.07)

                        if self.isData():
                            c = sys.stdin.read(1)
                            if c == '\x1b':         # x1b is ESC
                                line = ""
                                break
                            #send message or process command
                            elif c == '\n':
                                if line == '^':
                                    self.channel = self.above_channel
                                    line = ""
                                break
                            else:
                                line += c
                    if line != "":
                        await self.bot.send_message(self.bot.get_channel(self.channel),line)

                finally:
                    termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)
        
        #threaded. breaks on !restart/reload but can see in terminal. less resource intensive
        # self.flush_time = time.perf_counter() + 3
        # while self.settings["INPUT"] and self.getting_input():
        #     self.input_msg = {"cmd":None,"msg":None}
        #     self.input_thread = threading.Thread(target=self.wait_for_input, args=(ctx.message.author,))
        #     self.input_thread.start()
        #     while self.input_msg["cmd"] == None:
        #         if self.flush_time != None:
        #             await asyncio.sleep(.005)
        #         else:
        #             await asyncio.sleep(.05)
        #     if self.input_msg["msg"] != None and self.getting_input():
        #         prefix = randchoice(["boop: ","boop ","Boop: ","BOOP: ","BOOOOOPPP ","o\\-<|:","bop: "])
        #         sentmsg = await self.bot.send_message(self.bot.get_channel(self.channel),prefix+self.input_msg["msg"])
        #         self.self_msg = sentmsg.server.id + sentmsg.channel.id + sentmsg.author.id + sentmsg.content

    #how to consume lines previous to activation?
    def wait_for_input(self,ctx):
        channel = self.bot.get_channel(self.channel)
        nob = "# "
        if self.flush_time != None:
            nob = "Flushed any above input ^ > "
        msg = input(nob)
        if self.flush_time != None:
            if self.flush_time < time.perf_counter():
                self.flush_time = None
            else:
                self.input_msg["cmd"]="flush"
                return
        if msg == "^":
            self.channel = self.above_channel
            print("@ now sending messages to "+ channel.server.name +" #"+channel.name)
            self.input_msg["cmd"]="channel"
        elif "console" in msg and msg[:msg.index("console")] in self.bot.command_prefix:
            if self.stop_getting_input():
                print("@ I will stop sending messages written here to Discord.")
                self.input_msg["cmd"]="end"
            else:
                print("@ Was not able to stop input loop.")
                self.input_msg["cmd"]="end_err"
        elif msg == "":
            self.input_msg["cmd"]="empty"
        else:
            self.input_msg["msg"]=msg
            self.input_msg["cmd"]="post"


    def start_getting_input(self):
        try:
            self.queue.put_nowait('getting input')
            return True
        except asyncio.QueueFull:
            return False
        # just didn't catch other exceptions
        # except Exception as e:
        #     #replace with raise e?
        #     return e

    def stop_getting_input(self):
        try:
            #self.input_thread.join()
            self.queue.get_nowait()
            return True
        except asyncio.QueueEmpty:
            return False

    def getting_input(self):
        if self.queue.qsize() == 0:
            return False
        else:
            return True


    @commands.command(pass_context=True)
    @checks.is_owner()
    async def console(self, ctx):
        """Turns on being telling the bot what to say through the console.
        Be careful of keyboard commands like ctrl+c"""
        #ls > 0? ls to stdin? errors to stdin?
        if not self.settings["INPUT"]:
            return
        if self.waiting_input:
            print("Still waiting for last input")
            await self.bot.send_message(ctx.message.channel,"Still waiting for last input. Please send a message with only the esc character in it.")
            return
        trigger = False
        if not self.getting_input():
            success = self.start_getting_input()
            if success:
                await self.bot.say("k... do what you have to do...")
                trigger = True
            else:
                success = self.stop_getting_input()
                if success == True:
                    success = self.start_getting_input()
                    if success == True:
                        await self.bot.say("k... do what you have to do...")
                        trigger = True
                    else:
                        await self.bot.say("Something went wrong. The console seems to be stuck. Try [p]reload consoletalk. If that doesn't work, restart the bot")
            # else:
            #     #maybe replace with raise e in the start/stop functions
            #     print(success)

        else:    
            success = self.stop_getting_input()
            if success:
                await self.bot.say("k...")
            else:
                success = self.start_getting_input()
                if success == True:
                    success = self.stop_getting_input()
                    if success == True:
                        await self.bot.say("k...")
                    else:
                        await self.bot.say("your hands are still here...")

        if trigger:
            self.channel = ctx.message.channel.id
            self.above_channel = ctx.message.channel.id
            await self.input_loop(ctx)

def check_folders():
    if not os.path.exists("data/consoletalk"):
        print("Creating data/consoletalk folder...")
        os.makedirs("data/consoletalk")

def check_files():
    default_settings = {"PRINT":True,"INPUT":True}

    f = "data/consoletalk/settings.json"
    if not fileIO(f, "check"):
        print("Creating default consoletalk's settings.json...")
        fileIO(f, "save", default_settings)   

def setup(bot):
    check_folders()
    check_files()
    n = Consoletalk(bot)
    #bot.add_listener(n.get_os, "on_ready")
    bot.add_listener(n.print_to_console, "on_message")
    bot.add_cog(n)
