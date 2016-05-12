# Developed by Redjumpman for Redbot by Twentysix26
# Requires BeautifulSoup4, Tabulate, and Numpy to work.
from discord.ext import commands
from __main__ import send_cmd_help
import aiohttp
try:   # check if BeautifulSoup4 is installed
    from bs4 import BeautifulSoup
    soupAvailable = True
except:
    soupAvailable = False
try:   # Check if Tabulate is installed
    from tabulate import tabulate
    tabulateAvailable = True
except:
    tabulateAvailable = False


class Pokedex:
    """Search for Pokemon."""

    def __init__(self, bot):
        self.bot = bot

    # Because there is multiple commands with the parameter 'pokedex' we need
    # to create a group.
    @commands.group(pass_context=True)
    async def pokedex(self, ctx):
        """This is the list of pokemon queries you can perform."""

        if ctx.invoked_subcommand is None:
            await send_cmd_help(ctx)

    # When using group commands you need to put the name of the sub command
    # within the argument
    @pokedex.command(name="pokemon", pass_context=False)
    # when defining the sub group you need to have _ before and after the new
    # command
    async def _pokemon_pokedex(self, pokemon):
        """Get a pokemon's pokedex info.
        Example !pokedex pokemon gengar"""
        # We need to check if the length of the input is greater than 0.
        # This is just a catch for when there is no input
        if len(pokemon) > 0:
            # All data is pulled from pokemondb.net
            url = "http://pokemondb.net/pokedex/" + str(pokemon)
            async with aiohttp.get(url) as response:
                try:
                    soup = BeautifulSoup(await response.text(), "html.parser")
                    # This scrapes the pokemon image
                    img = soup.find("img")["src"]
                    # This list holds all the data from the left column
                    poke = []
                    # This list holds all data from the right column
                    pokeh = []
                    # This is the parent table from which the data is scraped
                    table = soup.find('table', attrs={'class': 'vitals-table'})
                    table_body = table.find('tbody')
                    # This will start the scrape for the left column of data
                    headers = table_body.find_all('tr')
                # Iterates through the rows to grab the data held in headers
                # This will also says that if there is no text, don't strip
                    for head in headers:
                        hols = head.find_all('th')
                        hols = [ele.text.strip() for ele in hols]
                        pokeh.append([ele for ele in hols if ele])
                # This will start the scrape for the right column of data
                        rows = table_body.find_all('tr')
                # Same thing with headers, except we are looking for td tags
                    for row in rows:
                        cols = row.find_all('td')
                        cols = [ele.text.strip() for ele in cols]
                        poke.append([ele for ele in cols if ele])

                # Slams the two list into one column This is made easy because
                # both are 1 dimensional
                    m = list(zip(pokeh, poke))
                # using the import from tabulate format the combined list into
                # a nice looking table
                    t = tabulate(m, headers=["Pokedex", "Data"])
                # We add that data. Img is a image, but t is all text so we
                # have to say so with str. \n creates a new line and the ```
                # puts the output into the pretty code block
                    await self.bot.say(img + "\n" + "```" + str(t) + "```")
                except:
                    await self.bot.say("Could not locate that pokemon." +
                                       " Please try a different name"
                                       )
        else:
            await self.bot.say("Oh no! You didn't input a name. Type a" +
                               " pokemon name to search")

    @pokedex.command(name="stats", pass_context=False)
    async def _stats_pokedex(self, pokemon):
        """Get a pokemon's base stats.
        Example: !pokedex stats squirtle"""
        if len(pokemon) > 0:
            url = "http://pokemondb.net/pokedex/" + str(pokemon)
            async with aiohttp.get(url) as response:
                try:
                    soup = BeautifulSoup(await response.text(), "html.parser")
                    stats = []
                    # This data is always the same, so no need to strip it!
                    base = [["HP"], ["Def"], ["ATK"], ["Sp.Atk"], ["Sp.Def"],
                            ["Speed"]
                            ]
                    divs = soup.find('div', attrs={'class': 'col span-8 '})
                    table = divs.find('table', attrs={'class': 'vitals-table'})
                    table_body = table.find('tbody')

                    rows = table_body.find_all('tr')
                    for row in rows:
                        cols = row.find_all('td')
                        cols = [ele.text.strip() for ele in cols]
                        stats.append([ele for ele in cols if ele])
                    # Because the two lists, base and stats, are different
                    # dimensions and stats is undefined, we have to peform
                    # zip to make an iterator aggregate through the elements
                    statbase = [from_a2 + from_a1
                                for from_a2, from_a1 in zip(base, stats)]
                # Because part of the data is a graph it adds it to stats as
                # a none value, [], we use filter to get rid of it.
                    k = filter(None, statbase)
                # We use tabulate to create the table and create headers
                    t = tabulate(k, headers=["Stat", "Base", "Min", "Max"])
                    await self.bot.say("```" + t + "```")
                except:
                    await self.bot.say("Could not locate that pokemon's" +
                                       " stats. Please try a different name"
                                       )
        else:
            await self.bot.say("Looks like you forgot to put in a pokemon" +
                               " name. Input a name to search"
                               )

    @pokedex.command(name="moveset", pass_context=False)
    async def _moveset_pokedex(self, generation: str, pokemon):
        """Get a pokemon's moveset by generation(1-6).

          Example: !pokedex moveset V pikachu """
        if len(pokemon) > 0:
            if generation == "6" or generation == "VI":
                try:
                    url = "http://pokemondb.net/pokedex/" + str(pokemon)
                    async with aiohttp.get(url) as response:
                        soup = BeautifulSoup(await response.text(),
                                             "html.parser"
                                             )
                        moves = []
                        table = soup.find('table',
                                          attrs={'class':
                                                 'data-table wide-table'
                                                 }
                                          )
                        table_body = table.find('tbody')
                        rows = table_body.find_all('tr')
                        for row in rows:
                            cols = row.find_all('td')
                            cols = [ele.text.strip() for ele in cols]
                            moves.append([ele for ele in cols if ele])

                        t = tabulate(moves, headers=["Level", "Moves", "Type",
                                                     "Category", "Power",
                                                     "Accuracy"])
                        await self.bot.say("```" + str(t) + "```")
                except:
                    await self.bot.say("Could not locate a pokemon with that" +
                                       " name. Try a different name.")

            elif generation == "5" or generation == "V":
                try:
                    url = "http://pokemondb.net/pokedex/" + str(pokemon)
                    # Added a continuation for url, instead of all on one line
                    # to make PEP8 compliant
                    url += "/moves/5"
                    async with aiohttp.get(url) as response:
                        soup = BeautifulSoup(await response.text(),
                                             "html.parser")
                        moves = []
                        table = soup.find('table', attrs={'class':
                                          'data-table wide-table'}
                                          )
                        table_body = table.find('tbody')

                        rows = table_body.find_all('tr')
                        for row in rows:
                            cols = row.find_all('td')
                            cols = [ele.text.strip() for ele in cols]
                            moves.append([ele for ele in cols if ele])

                        t = tabulate(moves, headers=["Level", "Moves", "Type",
                                                     "Category", "Power",
                                                     "Accuracy"])
                        await self.bot.say("```" + str(t) + "```")
                except:
                    await self.bot.say("Could not locate a pokemon with that" +
                                       " name. Try a different name.")

            elif generation == "4" or generation == "IV":
                try:
                    url = "http://pokemondb.net/pokedex/" + str(pokemon)
                    url += "/moves/4"
                    async with aiohttp.get(url) as response:
                        soup = BeautifulSoup(await response.text(),
                                             "html.parser")
                        moves = []
                        table = soup.find('table',
                                          attrs={'class':
                                                 'data-table wide-table'}
                                          )
                        table_body = table.find('tbody')

                        rows = table_body.find_all('tr')
                        for row in rows:
                            cols = row.find_all('td')
                            cols = [ele.text.strip() for ele in cols]
                            moves.append([ele for ele in cols if ele])

                        t = tabulate(moves, headers=["Level", "Moves", "Type",
                                                     "Category", "Power",
                                                     "Accuracy"])
                        await self.bot.say("```" + str(t) + "```")
                except:
                    await self.bot.say("Could not locate a pokemon with that" +
                                       " name. Try a different name.")

            elif generation == "3" or generation == "III":
                try:
                    url = "http://pokemondb.net/pokedex/" + str(pokemon)
                    url += "/moves/3"
                    async with aiohttp.get(url) as response:
                        soup = BeautifulSoup(await response.text(),
                                             "html.parser")
                        moves = []
                        table = soup.find('table', attrs={'class':
                                          'data-table wide-table'}
                                          )
                        table_body = table.find('tbody')

                        rows = table_body.find_all('tr')
                        for row in rows:
                            cols = row.find_all('td')
                            cols = [ele.text.strip() for ele in cols]
                            moves.append([ele for ele in cols if ele])

                        t = tabulate(moves, headers=["Level", "Moves", "Type",
                                                     "Category", "Power",
                                                     "Accuracy"])
                        await self.bot.say("```" + str(t) + "```")
                except:
                    await self.bot.say("Could not locate a pokemon with that" +
                                       " name. Try a different name.")

            elif generation == "2" or generation == "II":
                try:
                    url = "http://pokemondb.net/pokedex/" + str(pokemon)
                    url += "/moves/2"
                    async with aiohttp.get(url) as response:
                        soup = BeautifulSoup(await response.text(),
                                             "html.parser")
                        moves = []
                        table = soup.find('table', attrs={'class':
                                          'data-table wide-table'}
                                          )
                        table_body = table.find('tbody')

                        rows = table_body.find_all('tr')
                        for row in rows:
                            cols = row.find_all('td')
                            cols = [ele.text.strip() for ele in cols]
                            moves.append([ele for ele in cols if ele])

                        t = tabulate(moves, headers=["Level", "Moves", "Type",
                                                     "Category", "Power",
                                                     "Accuracy"])
                        await self.bot.say("```" + str(t) + "```")
                except:
                    await self.bot.say("Could not locate a pokemon with that" +
                                       " name. Try a different name.")

            elif generation == "1" or generation == "I":
                try:
                    url = "http://pokemondb.net/pokedex/" + str(pokemon)
                    url += "/moves/1"
                    async with aiohttp.get(url) as response:
                        soup = BeautifulSoup(await response.text(),
                                             "html.parser")
                        moves = []
                        table = soup.find('table', attrs={'class':
                                          'data-table wide-table'}
                                          )
                        table_body = table.find('tbody')

                        rows = table_body.find_all('tr')
                        for row in rows:
                            cols = row.find_all('td')
                            cols = [ele.text.strip() for ele in cols]
                            moves.append([ele for ele in cols if ele])

                        t = tabulate(moves, headers=["Level", "Moves", "Type",
                                                     "Category", "Power",
                                                     "Accuracy"])
                        await self.bot.say("```" + str(t) + "```")
                except:
                    await self.bot.say("Could not locate a pokemon with that" +
                                       " name. Try a different name.")
            else:
                await self.bot.say("Generation must be " + "**" + "1-6" +
                                   "**" + " or **" + "I-VI**.")

        else:
            await self.bot.say("You need to input a pokemon name to search." +
                               "Input a name and try again."
                               )

    @pokedex.command(name="item", pass_context=False)
    async def _item_pokedex(self, item):
        """Get a description of an item.
        Use '-' for spaces. Example: !pokedex item master-ball
        """
        if len(item) > 0:
            url = "http://pokemondb.net/item/" + str(item)
            async with aiohttp.get(url) as response:
                try:
                    soup = BeautifulSoup(await response.text(), "html.parser")
                    divs = soup.find('p')
                    info = divs.get_text()

                    await self.bot.say("**" + str(item.title()) + ":**" +
                                       "\n" + "```" + str(info) + "```"
                                       )
                except:
                    await self.bot.say("Cannot find an item with this name")
        else:
            await self.bot.say("Please input an item name.")

    @pokedex.command(name="location", pass_context=False)
    async def _location_pokedex(self, pokemon):
        """Get a pokemon's catch location.
        Example !pokedex location voltorb
        """
        if len(pokemon) > 0:
            url = "http://pokemondb.net/pokedex/" + str(pokemon)
            async with aiohttp.get(url) as response:
                soup = BeautifulSoup(await response.text(), "html.parser")
                loc = []
                version = []
                div2 = soup.find('div', attrs={'class':
                                               'col desk-span-7 lap-span-12'})
                tables = div2.find_all('table', attrs={'class':
                                       'vitals-table'})
                for table in tables:
                    cols = table.find_all('td')
                    cols = [ele.text.strip() for ele in cols]
                    loc.append([ele for ele in cols if ele])
                tables2 = div2.find_all('table', attrs={'class':
                                        'vitals-table'})
                for table2 in tables2:
                    tcols = table2.find_all('th')
                    tcols = [ele.text.strip() for ele in tcols]
                    version.append([ele for ele in tcols if ele])
                # We have to extract out the base index, because it scrapes as
                # a list of a list. Then we can stack and tabulate.
                extract_loc = loc[0]
                extract_version = version[0]
                m = list(zip(extract_version, extract_loc))
                t = tabulate(m, headers=["Game Version", "Location"])

                await self.bot.say("```" + str(t) + "```")
        else:
            await self.bot.say("Unable to find any locations" +
                               "Check your spelling or try a different name."
                               )

    @pokedex.command(name="evolution", pass_context=False)
    async def _evolution_pokedex(self, pokemon):
        """Show a pokemon's evolution chain
        Example !pokedex evolution bulbasaur"""
        if len(pokemon) > 0:
            url = "http://pokemondb.net/pokedex/" + str(pokemon)
            async with aiohttp.get(url) as response:
                try:
                    soup = BeautifulSoup(await response.text(), "html.parser")
                    div = soup.find('div', attrs={'class':
                                                  'infocard-evo-list'})
                    evo = str(div.text.strip())
                    await self.bot.say("```" + evo + "```")
                except:
                    await self.bot.say(str(pokemon) +
                                       " does not have an evolution chain")
        else:
            await self.bot.say("Please input a pokemon name.")


def setup(bot):
    if soupAvailable:
        if tabulateAvailable:
            n = Pokedex(bot)
            bot.add_cog(n)
        else:
            raise RuntimeError("You need to run 'pip3 install tabulate'")
    else:
        raise RuntimeError("You need to run 'pip3 install beautifulsoup4'")
