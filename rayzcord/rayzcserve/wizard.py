"""Interactive text-driven wizard for server typography styling."""

import asyncio
from typing import Callable, Optional, Tuple

import discord
from discord.ext import commands

from .applier import ServerStyleApplier
from .constants import (
    FONTS_PER_PAGE,
    PROMPT_CANCELLED,
    PROMPT_INITIAL_DESC,
    PROMPT_INITIAL_TITLE,
    PROMPT_TIMEOUT,
    WIZARD_TIMEOUT_SECONDS,
)
from .fonts import FONTS, format_font_page, get_font
from .symbols import format_symbols_page, get_symbol


class ServerStyleWizard:
    """Conversational state machine guiding users through font, symbol, and scope selection."""

    def __init__(self, bot: commands.Bot, ctx: commands.Context):
        self.bot = bot
        self.ctx = ctx
        self.applier = ServerStyleApplier(ctx.guild)

    def _author_check(self, message: discord.Message) -> bool:
        return message.author == self.ctx.author and message.channel == self.ctx.channel

    async def _wait_response(self, timeout: float = WIZARD_TIMEOUT_SECONDS) -> Optional[str]:
        try:
            msg = await self.bot.wait_for("message", timeout=timeout, check=self._author_check)
            return msg.content.strip()
        except asyncio.TimeoutError:
            return None

    async def run(self) -> Optional[dict]:
        """Runs the wizard and returns the configuration if user confirms."""
        # Step 1: Initial Gate [y/n]
        init_embed = discord.Embed(
            title=PROMPT_INITIAL_TITLE,
            description=PROMPT_INITIAL_DESC,
            colour=discord.Colour.blurple(),
        )
        await self.ctx.send(embed=init_embed)

        resp = await self._wait_response()
        if not resp:
            await self.ctx.send(PROMPT_TIMEOUT)
            return None
        if resp.lower() not in ["y", "yes"]:
            await self.ctx.send(PROMPT_CANCELLED)
            return None

        # Step 2: Font Selection (Paginated 100+ fonts)
        current_page = 1
        total_pages = (len(FONTS) + FONTS_PER_PAGE - 1) // FONTS_PER_PAGE
        selected_font_id: Optional[int] = None

        sample_name = "general"
        if self.ctx.guild.text_channels:
            sample_name = self.ctx.guild.text_channels[0].name

        while selected_font_id is None:
            page_text = format_font_page(current_page, FONTS_PER_PAGE, sample_text=sample_name)
            font_embed = discord.Embed(
                title="Step 1: Select Font",
                description=f"```\n{page_text}\n```",
                colour=discord.Colour.dark_teal(),
            )
            font_embed.set_footer(
                text="Type a number (1-105) to select, or 'next' / 'prev' to browse pages."
            )
            await self.ctx.send(embed=font_embed)

            resp = await self._wait_response()
            if not resp:
                await self.ctx.send(PROMPT_TIMEOUT)
                return None

            low = resp.lower()
            if low in ["cancel", "quit", "exit"]:
                await self.ctx.send(PROMPT_CANCELLED)
                return None
            elif low in ["n", "next"]:
                current_page = 1 if current_page >= total_pages else current_page + 1
            elif low in ["p", "prev", "previous"]:
                current_page = total_pages if current_page <= 1 else current_page - 1
            elif resp.isdigit():
                f_id = int(resp)
                if get_font(f_id):
                    selected_font_id = f_id
                else:
                    await self.ctx.send(f"Invalid font number. Choose between 1 and {len(FONTS)}.")
            else:
                await self.ctx.send("Unrecognized input. Enter a font number or 'next' / 'prev'.")

        font_obj = get_font(selected_font_id)
        font_preview = font_obj.transform(sample_name)
        await self.ctx.send(
            f"Selected Font #{font_obj.font_id} ({font_obj.name}): '{font_preview}'"
        )

        # Step 3: Symbol Selection [1, 2, or no]
        selected_symbol_id: Optional[int] = None
        sym_prompt_embed = discord.Embed(
            title="Step 2: Symbols and Borders",
            description=(
                "Would you like to add symbols, borders, or accents?\n\n"
                "Options:\n"
                "- Select '1' : Brackets and Framing (e.g. [ ], { }, 『 』, 【 】)\n"
                "- Select '2' : Accents and Separators (e.g. ✦, ✧, ★, », •, ◈)\n"
                "- Select 'no': Skip symbols (use clean font only)\n\n"
                "Type 1, 2, or 'no':"
            ),
            colour=discord.Colour.gold(),
        )
        await self.ctx.send(embed=sym_prompt_embed)

        resp = await self._wait_response()
        if not resp:
            await self.ctx.send(PROMPT_TIMEOUT)
            return None

        sym_choice = resp.lower()
        if sym_choice in ["1", "brackets"]:
            sym_page = format_symbols_page(category_filter="Brackets", sample_text=font_preview)
            await self.ctx.send(f"```\n{sym_page}\n```\nEnter symbol number to select:")
            sym_num_resp = await self._wait_response()
            if sym_num_resp and sym_num_resp.isdigit():
                sym = get_symbol(int(sym_num_resp))
                if sym:
                    selected_symbol_id = sym.symbol_id
        elif sym_choice in ["2", "accents", "wings"]:
            sym_page = format_symbols_page(category_filter="Accents", sample_text=font_preview)
            await self.ctx.send(f"```\n{sym_page}\n```\nEnter symbol number to select:")
            sym_num_resp = await self._wait_response()
            if sym_num_resp and sym_num_resp.isdigit():
                sym = get_symbol(int(sym_num_resp))
                if sym:
                    selected_symbol_id = sym.symbol_id

        # Step 4: Combination Rule
        def transform_pipeline(text: str) -> str:
            styled_text = font_obj.transform(text)
            if selected_symbol_id:
                sym_obj = get_symbol(selected_symbol_id)
                if sym_obj:
                    return sym_obj.apply(styled_text)
            return styled_text

        sample_transformed = transform_pipeline(sample_name)
        await self.ctx.send(f"Combined Style Preview: '{sample_transformed}'")

        # Step 5: Scope Selection (Option B: Channels, Categories, Roles, or All)
        scope_embed = discord.Embed(
            title="Step 3: Select Application Scope",
            description=(
                "Choose which elements across the server to style:\n\n"
                "1: Text Channels only\n"
                "2: Voice Channels only\n"
                "3: Categories only\n"
                "4: Roles only\n"
                "5: Entire Server (All Channels, Categories, and Roles)\n\n"
                "Enter option (1-5):"
            ),
            colour=discord.Colour.blue(),
        )
        await self.ctx.send(embed=scope_embed)

        scope_resp = await self._wait_response()
        if not scope_resp or not scope_resp.isdigit() or int(scope_resp) not in range(1, 6):
            await self.ctx.send(PROMPT_CANCELLED)
            return None

        scope_int = int(scope_resp)
        channels, roles = self.applier.collect_elements(scope_int)

        if not channels and not roles:
            await self.ctx.send("No matching elements found under the selected scope.")
            return None

        # Step 6: Confirmation & Live Preview
        previews = self.applier.build_preview(channels, roles, transform_pipeline)
        confirm_embed = discord.Embed(
            title="Step 4: Final Confirmation",
            description=(
                f"Targets collected: {len(channels)} channels/categories, {len(roles)} roles.\n\n"
                "**Sample Transformations:**\n" + "\n".join(previews) + "\n\n"
                "Apply this styling to the entire selected scope? [y/n]"
            ),
            colour=discord.Colour.brand_green(),
        )
        confirm_embed.set_footer(
            text="A backup snapshot will be recorded so you can undo at any time with 'rcs undo'."
        )
        await self.ctx.send(embed=confirm_embed)

        final_resp = await self._wait_response()
        if not final_resp or final_resp.lower() not in ["y", "yes"]:
            await self.ctx.send(PROMPT_CANCELLED)
            return None

        # Execute Batch Application
        snapshot = await self.applier.apply_batch(self.ctx, channels, roles, transform_pipeline)
        return {
            "font_id": selected_font_id,
            "symbol_id": selected_symbol_id,
            "scope": scope_int,
            "snapshot": snapshot,
        }
