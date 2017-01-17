from discord.ext import commands
from __main__ import send_cmd_help
import aiohttp
import asyncio
import io, os

class Moji:
	def __init__(self, bot):
		self.bot = bot


	@commands.command(pass_context=True)
	async def emoji(self, ctx, name: str):
		"""Send a large custom emoji. 

		Bot must be in the server with the emoji"""
		for x in list(self.bot.get_all_emojis()):
			if x.name.lower() == name.lower():
				fdir ="data/moji/" + x.server.name
				fp = fdir + "/{0.name}.png".format(x)
				if not os.path.exists(fdir):
					os.mkdir(fdir)
				if not os.path.isfile(fp):
					async with aiohttp.get(x.url) as r:
						img_bytes = await r.read()
						img = io.BytesIO(img_bytes)
						with open(fp, 'wb') as o:
							o.write(img.read())
						o.close()

#You can uncomment this line if you want c: 
				#await self.bot.delete_message(ctx.message)
				return await self.bot.send_file(ctx.message.channel, fp)

	@commands.group(pass_context=True)
	async def moji(self, ctx):
		"""Various emoji operations"""
		if ctx.invoked_subcommand is None:
			return await send_cmd_help(ctx)

	@moji.command(pass_context=True)
	async def list(self, ctx, server: int = None):
		"""List all available custom emoji"""
		server = server
		servers = list(self.bot.servers)
		if server is None:
			msg = "``` Available servers:"
			for x in servers:
				msg += "\n\t" + str(servers.index(x)) + ("- {0.name}".format(x))
			await self.bot.say(msg + "```")
		else:
			msg = "```Emojis for {0.name}".format(servers[server])
			for x in list(servers[server].emojis):
				msg += "\n\t" + str(x.name)
			await self.bot.say(msg + "```")



def check_folders():
	if not os.path.exists("data/moji"):
		print("Creating data/moji folder...")
		os.makedirs("data/moji")

def setup(bot):
	check_folders()
	bot.add_cog(Moji(bot))
