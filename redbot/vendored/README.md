### discord-ext-menus

An experimental extension menu that makes working with reaction menus a bit easier.

**There are no front-facing docs for this and it's not on PyPI. As this is meant to be a repository for testing**

## Installing

Installing is done purely via git:

```py
python -m pip install -U git+https://github.com/Rapptz/discord-ext-menus
```

## Getting Started

To whet your appetite, the following examples show the fundamentals on how to create menus.

The first example shows a basic menu that has a stop button and two reply buttons:

```py
from discord.ext import menus

class MyMenu(menus.Menu):
    async def send_initial_message(self, ctx, channel):
        return await channel.send(f'Hello {ctx.author}')

    @menus.button('\N{THUMBS UP SIGN}')
    async def on_thumbs_up(self, payload):
        await self.message.edit(content=f'Thanks {self.ctx.author}!')

    @menus.button('\N{THUMBS DOWN SIGN}')
    async def on_thumbs_down(self, payload):
        await self.message.edit(content=f"That's not nice {self.ctx.author}...")

    @menus.button('\N{BLACK SQUARE FOR STOP}\ufe0f')
    async def on_stop(self, payload):
        self.stop()
```

Now, within a command we just instantiate it and we start it like so:

```py
@bot.command()
async def menu_example(ctx):
    m = MyMenu()
    await m.start(ctx)
```

If an error happens then an exception of type `menus.MenuError` is raised.

This second example shows a confirmation menu and how we can compose it and use it later:

```py
from discord.ext import menus

class Confirm(menus.Menu):
    def __init__(self, msg):
        super().__init__(timeout=30.0, delete_message_after=True)
        self.msg = msg
        self.result = None

    async def send_initial_message(self, ctx, channel):
        return await channel.send(self.msg)

    @menus.button('\N{WHITE HEAVY CHECK MARK}')
    async def do_confirm(self, payload):
        self.result = True
        self.stop()

    @menus.button('\N{CROSS MARK}')
    async def do_deny(self, payload):
        self.result = False
        self.stop()

    async def prompt(self, ctx):
        await self.start(ctx, wait=True)
        return self.result
```

Then when it comes time to use it we can do it like so:

```py
@bot.command()
async def delete_things(ctx):
    confirm = await Confirm('Delete everything?').prompt(ctx)
    if confirm:
        await ctx.send('deleted...')
```

### Pagination

The meat of the library is the `Menu` class but a `MenuPages` class is provided for the common use case of actually making a pagination session.

The `MenuPages` works similar to `Menu` except things are separated into a `PageSource`. The actual `MenuPages` rarely needs to be modified, instead we pass in a `PageSource` that deals with the data representation and formatting of the data we want to paginate.

The library comes with a few built-in page sources:

- `ListPageSource`: The basic source that deals with a list of items.
- `GroupByPageSource`: A page source that groups a list into multiple sublists similar to `itertools.groupby`.
- `AsyncIteratorPageSource`: A page source that works with async iterators for lazy fetching of data.

None of these page sources deal with formatting of data, leaving that up to you.

For the sake of example, here's a basic list source that is paginated:

```py
from discord.ext import menus

class MySource(menus.ListPageSource):
    def __init__(self, data):
        super().__init__(data, per_page=4)

    async def format_page(self, menu, entries):
        offset = menu.current_page * self.per_page
        return '\n'.join(f'{i}. {v}' for i, v in enumerate(entries, start=offset))

# somewhere else:
pages = menus.MenuPages(source=MySource(range(1, 100)), clear_reactions_after=True)
await pages.start(ctx)
```

The `format_page` can return either a `str` for content, `discord.Embed` for an embed, or a `dict` to pass into the kwargs of `Message.edit`.

Some more examples using `GroupByPageSource`:

```py
from discord.ext import menus

class Test:
    def __init__(self, key, value):
        self.key = key
        self.value = value

data = [
    Test(key=key, value=value)
    for key in ['test', 'other', 'okay']
    for value in range(20)
]

class Source(menus.GroupByPageSource):
    async def format_page(self, menu, entry):
        joined = '\n'.join(f'{i}. <Test value={v.value}>' for i, v in enumerate(entry.items, start=1))
        return f'**{entry.key}**\n{joined}\nPage {menu.current_page + 1}/{self.get_max_pages()}'

pages = menus.MenuPages(source=Source(data, key=lambda t: t.key, per_page=12), clear_reactions_after=True)
await pages.start(ctx)
```

Another one showing `AsyncIteratorPageSource`:

```py
from discord.ext import menus

class Test:
    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return f'<Test value={self.value}>'

async def generate(number):
    for i in range(number):
        yield Test(i)

class Source(menus.AsyncIteratorPageSource):
    def __init__(self):
        super().__init__(generate(9), per_page=4)

    async def format_page(self, menu, entries):
        start = menu.current_page * self.per_page
        return f'\n'.join(f'{i}. {v!r}' for i, v in enumerate(entries, start=start))

pages = menus.MenuPages(source=Source(), clear_reactions_after=True)
await pages.start(ctx)
```
