#testing out the new connecter with pmysql installed. Seems to be the only one that installs without any errors or deps.
import pymysql.cursors
import discord
from discord.ext import commands
import os
import sys
import threading

class DBCon:
    def __init__(self, bot):
        self.bot = bot
# Connect to the database
connection = pymysql.connect(host='localhost',
                             user='devsqlusr',
                             password='R1v1t3d0n3!',
                             db='devpress',
                             charset='utf8mb4',
                             cursorclass=pymysql.cursors.DictCursor)

try:
    with connection.cursor() as cursor:
        # Create a new record
        sql = "INSERT INTO `users` (`email`, `password`) VALUES (%s, %s)"
        cursor.execute(sql, ('webmaster@python.org', 'very-secret'))

    # connection is not autocommit by default. So you must commit to save
    # your changes.
    connection.commit()

    with connection.cursor() as cursor:
        # Read a single record
        sql = "SELECT `id`, `password` FROM `users` WHERE `email`=%s"
        cursor.execute(sql, ('webmaster@python.org',))
        result = cursor.fetchone()
        print(result)
finally:
    connection.close()

def setup(bot):
    n = DBCon(bot)
    bot.add_cog(n)
