"""Interactive setup wizard for role assignment menus."""

import asyncio
import re
from typing import List, Optional, Tuple, Union

import discord
from discord.ext import commands

from .constants import (
    ENTRY_TIMEOUT_SECONDS,
    MENU_EMBED_FOOTER,
    MENU_EMBED_TITLE,
    PROMPT_ADD_ANOTHER_DESC,
    PROMPT_ADD_ANOTHER_TITLE,
    PROMPT_CANCELLED,
    PROMPT_INITIAL_DESC,
    PROMPT_INITIAL_TITLE,
    PROMPT_INVALID_CHOICE,
    PROMPT_ROLE_DESC,
    PROMPT_ROLE_TITLE,
    PROMPT_TIMEOUT,
    WIZARD_TIMEOUT_SECONDS,
)

ORDINALS = ["first", "second", "third", "fourth", "fifth", "next"]


class RoleWizard:
    """Manages an interactive session to build a role selection menu."""

    def __init__(
        self,
        bot: commands.Bot,
        ctx: commands.Context,
        target_channel: Union[discord.TextChannel, discord.Thread],
    ):
        self.bot = bot
        self.ctx = ctx
        self.target_channel = target_channel
        self.mappings: List[Tuple[str, discord.Role]] = []

    def _author_check(self, message: discord.Message) -> bool:
        return message.author == self.ctx.author and message.channel == self.ctx.channel

    async def run(self) -> Optional[List[Tuple[str, discord.Role]]]:
        """Runs the wizard state machine and returns role mappings if completed."""
        # Step 1: Initial confirmation [y/n]
        init_embed = discord.Embed(
            title=PROMPT_INITIAL_TITLE,
            description=PROMPT_INITIAL_DESC.format(channel=self.target_channel.mention),
            colour=discord.Colour.blurple(),
        )
        await self.ctx.send(embed=init_embed)

        try:
            response_msg = await self.bot.wait_for(
                "message", timeout=WIZARD_TIMEOUT_SECONDS, check=self._author_check
            )
        except asyncio.TimeoutError:
            await self.ctx.send(PROMPT_TIMEOUT)
            return None

        content = response_msg.content.strip().lower()
        if content in ["n", "no"]:
            await self.ctx.send(PROMPT_CANCELLED)
            return None
        if content not in ["y", "yes"]:
            await self.ctx.send(PROMPT_INVALID_CHOICE)
            return None

        # Step 2: Collection loop
        while True:
            current_index = len(self.mappings)
            ord_label = (
                ORDINALS[current_index]
                if current_index < len(ORDINALS)
                else f"number {current_index + 1}"
            )

            prompt_embed = discord.Embed(
                title=PROMPT_ROLE_TITLE.format(ordinal=ord_label),
                description=PROMPT_ROLE_DESC.format(ordinal=ord_label),
                colour=discord.Colour.dark_teal(),
            )
            await self.ctx.send(embed=prompt_embed)

            try:
                entry_msg = await self.bot.wait_for(
                    "message", timeout=ENTRY_TIMEOUT_SECONDS, check=self._author_check
                )
            except asyncio.TimeoutError:
                await self.ctx.send(PROMPT_TIMEOUT)
                return None

            raw_text = entry_msg.content.strip()
            if raw_text.lower() in ["cancel", "exit", "quit"]:
                await self.ctx.send("Setup cancelled.")
                return None

            tokens = raw_text.split(None, 1)
            if len(tokens) < 2:
                await self.ctx.send(
                    "Invalid input format. Provide an emoji followed by the role or 'cr <rolename>'."
                )
                continue

            emoji_str = tokens[0].strip()
            role_param = tokens[1].strip()

            # Verify the bot can react with the specified emoji
            try:
                test_message = await self.ctx.send("Validating emoji...")
                await test_message.add_reaction(emoji_str)
                await test_message.delete()
            except Exception:
                await self.ctx.send(
                    f"The bot cannot use the emoji '{emoji_str}'. Please provide a valid standard or server emoji."
                )
                continue

            # Determine whether role is an existing lookup or dynamic creation
            target_role: Optional[discord.Role] = None
            cr_match = re.match(r"^cr\s+(.+)$", role_param, re.IGNORECASE)

            if cr_match:
                new_name = cr_match.group(1).strip()
                try:
                    target_role = await self.ctx.guild.create_role(
                        name=new_name,
                        reason=f"Role generated via wizard by {self.ctx.author}",
                    )
                    await self.ctx.send(f"Created role '{target_role.name}'.")
                except discord.Forbidden:
                    await self.ctx.send(
                        "Permission error: The bot lacks 'Manage Roles' permission to create roles."
                    )
                    continue
                except Exception as exc:
                    await self.ctx.send(f"Error creating role: {exc}")
                    continue
            else:
                if entry_msg.role_mentions:
                    target_role = entry_msg.role_mentions[0]
                else:
                    stripped_name = role_param.lstrip("@")
                    target_role = discord.utils.get(self.ctx.guild.roles, name=stripped_name)
                    if not target_role and stripped_name.isdigit():
                        target_role = self.ctx.guild.get_role(int(stripped_name))

                if not target_role:
                    await self.ctx.send(
                        f"Could not find role '{role_param}'. To create it on the spot, use '{emoji_str} cr {role_param}'."
                    )
                    continue

            # Hierarchy check
            bot_member = self.ctx.guild.me
            if target_role >= bot_member.top_role and self.ctx.guild.owner != bot_member:
                await self.ctx.send(
                    f"Warning: The role '{target_role.name}' is above the bot's highest role. The bot will not be able to assign it."
                )

            self.mappings.append((emoji_str, target_role))
            await self.ctx.send(f"Paired '{emoji_str}' with '{target_role.name}'.")

            # Prompt to continue
            continue_embed = discord.Embed(
                title=PROMPT_ADD_ANOTHER_TITLE,
                description=PROMPT_ADD_ANOTHER_DESC.format(count=len(self.mappings)),
                colour=discord.Colour.dark_blue(),
            )
            await self.ctx.send(embed=continue_embed)

            try:
                next_response = await self.bot.wait_for(
                    "message", timeout=WIZARD_TIMEOUT_SECONDS, check=self._author_check
                )
            except asyncio.TimeoutError:
                await self.ctx.send("Response timeout reached. Finalizing current configuration.")
                break

            if next_response.content.strip().lower() in ["y", "yes"]:
                continue
            break

        return self.mappings if self.mappings else None

    @staticmethod
    def build_menu_embed(mappings: List[Tuple[str, discord.Role]]) -> discord.Embed:
        """Constructs the presentation embed for the target channel."""
        lines = ["React with the corresponding item to add or remove a role:\n"]
        for emoji, role in mappings:
            lines.append(f"{emoji} - {role.mention}")

        embed = discord.Embed(
            title=MENU_EMBED_TITLE,
            description="\n".join(lines),
            colour=discord.Colour.dark_green(),
        )
        embed.set_footer(text=MENU_EMBED_FOOTER)
        return embed
