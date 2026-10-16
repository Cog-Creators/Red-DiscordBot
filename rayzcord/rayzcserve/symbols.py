"""Symbol, bracket, border, and accent sets for text decoration."""

from dataclasses import dataclass
from typing import Callable, List, Optional


@dataclass(frozen=True)
class SymbolStyle:
    """Represents a border, bracket, or accent formatting pattern."""

    symbol_id: int
    name: str
    category: str
    formatter: Callable[[str], str]

    def apply(self, text: str) -> str:
        return self.formatter(text)


SYMBOLS: List[SymbolStyle] = []


def _reg_sym(sym_id: int, name: str, category: str, fn: Callable[[str], str]) -> None:
    SYMBOLS.append(SymbolStyle(symbol_id=sym_id, name=name, category=category, formatter=fn))


# Category 1: Brackets & Frames
_reg_sym(1, "Square Brackets", "Brackets", lambda t: f"[{t}]")
_reg_sym(2, "Curly Braces", "Brackets", lambda t: f"{{{t}}}")
_reg_sym(3, "Parentheses", "Brackets", lambda t: f"({t})")
_reg_sym(4, "Japanese Corner", "Brackets", lambda t: f"『{t}』")
_reg_sym(5, "Black Lens Brackets", "Brackets", lambda t: f"【{t}】")
_reg_sym(6, "Tortoise Shell", "Brackets", lambda t: f"〔{t}〕")
_reg_sym(7, "Double Angle", "Brackets", lambda t: f"《{t}》")
_reg_sym(8, "Pipes Vertical", "Brackets", lambda t: f"| {t} |")
_reg_sym(9, "Double Slashes", "Brackets", lambda t: f"// {t} //")
_reg_sym(10, "Angle Brackets", "Brackets", lambda t: f"<{t}>")

# Category 2: Accents, Wings & Separators
_reg_sym(11, "Asterisk Accent", "Accents", lambda t: f"* {t} *")
_reg_sym(12, "Plus Accent", "Accents", lambda t: f"+ {t} +")
_reg_sym(13, "Tilde Accent", "Accents", lambda t: f"~ {t} ~")
_reg_sym(14, "Four Point Star", "Accents", lambda t: f"✦ {t} ✦")
_reg_sym(15, "White Star", "Accents", lambda t: f"✧ {t} ✧")
_reg_sym(16, "Black Star", "Accents", lambda t: f"★ {t} ★")
_reg_sym(17, "Double Guillemets", "Accents", lambda t: f"» {t} «")
_reg_sym(18, "Bullet Point", "Accents", lambda t: f"• {t} •")
_reg_sym(19, "Diamond Accent", "Accents", lambda t: f"◈ {t} ◈")
_reg_sym(20, "Rhombus Accent", "Accents", lambda t: f"❖ {t} ❖")
_reg_sym(21, "Dash Border", "Accents", lambda t: f"- {t} -")
_reg_sym(22, "Em Dash Border", "Accents", lambda t: f"— {t} —")
_reg_sym(23, "Double Colon", "Accents", lambda t: f":: {t} ::")
_reg_sym(24, "Arrow Wings", "Accents", lambda t: f"> {t} <")
_reg_sym(25, "Hash Framing", "Accents", lambda t: f"# {t} #")


def get_symbol(symbol_id: int) -> Optional[SymbolStyle]:
    """Retrieves a symbol style by its 1-based index."""
    if 1 <= symbol_id <= len(SYMBOLS):
        return SYMBOLS[symbol_id - 1]
    return None


def get_all_symbols() -> List[SymbolStyle]:
    """Returns all configured symbol styles."""
    return SYMBOLS


def format_symbols_page(
    category_filter: Optional[str] = None, sample_text: str = "general"
) -> str:
    """Renders a text list of symbol options for selection."""
    lines = ["--- Available Symbols & Borders ---"]
    for sym in SYMBOLS:
        if category_filter and sym.category.lower() != category_filter.lower():
            continue
        preview = sym.apply(sample_text)
        lines.append(f"[{sym.symbol_id:2d}] {sym.name:<24} : {preview}")
    return "\n".join(lines)
