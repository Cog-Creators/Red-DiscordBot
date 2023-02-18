import discord
from discord.abc import Snowflake
from discord.utils import MISSING
from discord.enums import AppCommandType
from discord.app_commands import Command, Group, ContextMenu
from discord.app_commands.errors import CommandAlreadyRegistered
from typing import Dict, Tuple, Union, Optional, Sequence


class RedTree(discord.app_commands.CommandTree):
    """A container that holds application command information.
    
    Internally does not actually add commands to the tree unless they are
    enabled with `[p]slash enable`, to support Red's modularity.
    See discord.app_commands.CommandTree for more information.
    """
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Same structure as superclass
        self._disabled_global_commands: Dict[str, Union[Command, Group]] = {}
        self._disabled_context_menus: Dict[Tuple[str, Optional[int], int], ContextMenu] = {}
    
    def add_command(
        self,
        command: Union[Command, ContextMenu, Group],
        /,
        *args,
        guild: Optional[Snowflake] = MISSING,
        guilds: Sequence[Snowflake] = MISSING,
        override: bool = False,
        **kwargs,
    ) -> None:
        """Adds an application command to the tree.

        Commands will be internally stored until enabled by `[p]slash enable`.
        """
        # Allow guild specific commands to bypass the internals for development
        if guild is not MISSING or guilds is not MISSING:
            return super().add_command(command, *args, guild=guild, guilds=guilds, override=override, **kwargs)
        
        if isinstance(command, ContextMenu):
            name = command.name
            type = command.type.value
            key = (name, None, type)
            
            # Handle cases where the command already is in the tree
            if not override and key in self._disabled_context_menus:
                raise CommandAlreadyRegistered(name, None)
            if key in self._context_menus:
                if not override:
                    raise discord.errors.CommandAlreadyRegistered(name, None)
                del self._context_menus[key]
            
            self._disabled_context_menus[key] = command
            return
            
        if not isinstance(command, (Command, Group)):
            raise TypeError(f'Expected an application command, received {command.__class__.__name__} instead')
        
        root = command.root_parent or command
        name = root.name
        
        # Handle cases where the command already is in the tree
        if not override and name in self._disabled_global_commands:
            raise discord.errors.CommandAlreadyRegistered(name, None)
        if name in self._global_commands:
            if not override:
                raise discord.errors.CommandAlreadyRegistered(name, None)
            del self._global_commands[name]
        
        self._disabled_global_commands[name] = root
    
    def remove_command(
        self,
        command: str,
        /,
        *args,
        guild: Optional[Snowflake] = None,
        type: AppCommandType = AppCommandType.chat_input,
        **kwargs,
    ) -> Optional[Union[Command, ContextMenu, Group]]:
        """Removes an application command from this tree."""
        if guild is not None:
            return super().remove_command(command, *args, guild=guild, type=type, **kwargs)
        if type is AppCommandType.chat_input:
            return (
                self._disabled_global_commands.pop(command, None)
                or super().remove_command(command, *args, guild=guild, type=type, **kwargs)
            )
        elif type in (AppCommandType.user, AppCommandType.message):
            key = (command, None, type.value)
            return (
                self._disabled_context_menus.pop(key, None)
                or super().remove_command(command, *args, guild=guild, type=type, **kwargs)
            )

    def clear_commands(self, *args, guild: Optional[Snowflake], type: Optional[AppCommandType] = None, **kwargs) -> None:
        """Clears all application commands from the tree."""
        if guild is not None:
            return super().clear_commands(*args, guild=guild, type=type, **kwargs)
        
        if type is None or type is AppCommandType.chat_input:
            self._global_commands.clear()
            self._disabled_global_commands.clear()

        if type is None:
            self._disabled_context_menus.clear()
        else:
            self._disabled_context_menus = {
                (name, _guild_id, value): cmd
                for (name, _guild_id, value), cmd in self._disabled_context_menus.items()
                if value != type.value
            }
        return super().clear_commands(*args, guild=guild, type=type, **kwargs)
            
    async def red_check_enabled(self) -> None:
        """Restructures the commands in this tree, enabling commands that are enabled and disabling commands that are disabled.
        
        After running this function, the tree will be populated with enabled commands only.
        """
        enabled_commands = await self.client.list_enabled_app_commands()
        
        to_add_commands = []
        to_add_context = []
        to_remove_commands = []
        to_remove_context = []
        
        # Add commands
        for command in enabled_commands["slash"]:
            if command in self._disabled_global_commands:
                to_add_commands.append(command)
        
        # Add context
        for command in enabled_commands["message"]:
            key = (command, None, AppCommandType.message.value)
            if key in self._disabled_context_menus:
                to_add_context.append(key)
        for command in enabled_commands["user"]:
            key = (command, None, AppCommandType.user.value)
            if key in self._disabled_context_menus:
                to_add_context.append(key)
        
        # Remove commands
        for command in self._global_commands:
            if command not in enabled_commands["slash"]:
                to_remove_commands.append((command, AppCommandType.chat_input))
        
        # Remove context
        for command, guild_id, command_type in self._context_menus:
            if command_type is AppCommandType.message and command not in enabled_commands["message"]:
                to_remove_context.append((command, AppCommandType.message))
            elif command_type is AppCommandType.user and command not in enabled_commands["user"]:
                to_remove_context.append((command, AppCommandType.user))
        
        # Actually add/remove
        for command in to_add_commands:
            super().add_command(self._disabled_global_commands[command])
            del self._disabled_global_commands[command]
        for key in to_add_context:
            super().add_command(self._disabled_context_menus[key])
            del self._disabled_context_menus[key]
        for command, type in to_remove_commands:
            com = super().remove_command(command, type=type)
            self._disabled_global_commands[command] = com
        for command, type in to_remove_context:
            com = super().remove_command(command, type=type)
            self._discabled_context_menus[(command, None, type.value)] = com
