import discord
from datetime import datetime
from redbot.core.utils.chat_formatting import pagify
import io
import sys


class TunnelMeta(type):
    """
    lets prevent having multiple tunnels with the same
    places involved.
    """
    _instances = {}

    def __call__(cls, *args, **kwargs):
        lockout_tuple = (
            (kwargs.get('sender'), kwargs.get('origin')),
            kwargs.get('recipient')
        )
        if not (
            any(
                lockout_tuple[0] == x[0]
                for x in cls._instances.keys()
            ) or any(
                lockout_tuple[1] == x[1]
                for x in cls._instances.keys()
            )
        ):
            cls._instances[lockout_tuple] = super(
                TunnelMeta, cls).__call__(*args, **kwargs)
            return cls._instances[lockout_tuple]
        elif lockout_tuple in cls._instances:
            return cls._instances[lockout_tuple]
        else:
            return None


class Tunnel(metaclass=TunnelMeta):
    """
    A tunnel interface for messages

    This will return None on init if the destination
    or source + origin pair is already in use

    You should close tunnels when done with them
    """

    def __init__(self, *,
                 sender: discord.Member,
                 origin: discord.TextChannel,
                 recipient: discord.User):
        self.sender = sender
        self.origin = origin
        self.recipient = recipient
        self.last_interaction = datetime.utcnow()

    def __del__(self):
        lockout_tuple = ((self.sender, self.origin), self.recipient)
        self._instances.pop(lockout_tuple)

    def close(self):
        self.__del__()

    async def react_close(self, *, uid: int, message: str):
        send_to = self.recipient if uid == self.sender.id else self.sender
        closer = next(filter(
            lambda x: x.id == uid, (self.sender, self.recipient)), None)
        await send_to.send(
            message.format(closer=closer)
        )
        self.close()

    @property
    def members(self):
        return (self.sender, self.recipient)

    @property
    def minutes_since(self):
        return (self.last_interaction - datetime.utcnow()).minutes

    async def communicate(self, *,
                          message: discord.Message,
                          topic: str=None,
                          skip_message_content: bool=False):
        if message.channel == self.origin \
                and message.author == self.sender:
            send_to = self.recipient
        elif message.author == self.recipient \
                and isinstance(message.channel, discord.DMChannel):
            send_to = self.origin
        else:
            return

        if not skip_message_content:
            content = "\n".join((topic, message.content)) if topic \
                else message.content
        else:
            content = topic

        attach = None
        if message.attachments:
            files = []
            size = 0
            max_size = 8 * 1024 * 1024
            for a in message.attachments:
                _fp = io.BytesIO()
                await a.save(_fp)
                size += sys.getsizeof(_fp)
                if size > max_size:
                    await send_to.send(
                        "Could not forward attatchments. "
                        "Total size of attachments in a single "
                        "message must be less than 8MB."
                    )
                    break
                files.append(
                    discord.File(_fp, filename=a.filename)
                )
            else:
                attach = files

        rets = []
        for page in pagify(content):
            rets.append(
                await send_to.send(content, files=attach)
            )
            if attach:
                _fp.close()
                del attach

        await message.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await message.add_reaction("\N{NEGATIVE SQUARED CROSS MARK}")
        self.last_interaction = datetime.utcnow()
        await rets[-1].add_reaction("\N{NEGATIVE SQUARED CROSS MARK}")
        return (rets[-1], message)
