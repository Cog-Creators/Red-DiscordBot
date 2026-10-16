"""Unicode typography engine providing over 100 distinct font transformations."""

from dataclasses import dataclass
from typing import Callable, Dict, List, Optional

ASCII_LOWER = "abcdefghijklmnopqrstuvwxyz"
ASCII_UPPER = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
ASCII_DIGITS = "0123456789"
ASCII_ALL = ASCII_UPPER + ASCII_LOWER + ASCII_DIGITS

# Unicode Mathematical & Typographic Alphabets
SERIF_BOLD = "𝐀𝐁𝐂𝐃𝐄𝐅𝐆𝐇𝐈𝐉𝐊𝐋𝐌𝐍𝐎𝐏𝐐𝐑𝐒𝐓𝐔𝐕𝐖𝐗𝐘𝐙𝐚𝐛𝐜𝐝𝐞𝐟𝐠𝐡𝐢𝐣𝐤𝐥𝐦𝐧𝐨𝐩𝐪𝐫𝐬𝐭𝐮𝐯𝐰𝐱𝐲𝐳𝟎𝟏𝟐𝟑𝟒𝟓𝟔𝟕𝟖𝟗"
SERIF_ITALIC = "𝐴𝐵𝐶𝐷𝐸𝐹𝐺𝐻𝐼𝐽𝐾𝐿𝑀𝑁𝑂𝑃𝑄𝑅𝑆𝑇𝑈𝑉𝑊𝑋𝑌𝑍𝑎𝑏𝑐𝑑𝑒𝑓𝑔ℎ𝑖𝑗𝑘𝑙𝑚𝑛𝑜𝑝𝑞𝑟𝑠𝑡𝑢𝑣𝑤𝑥𝑦𝑧0123456789"
SERIF_BOLD_ITALIC = "𝑨𝑩𝑪𝑫𝑬𝑭𝑮𝑯𝑰𝑱𝑲𝑳𝑴𝑵𝑶𝑷𝑸𝑹𝑺𝑻𝑼𝑽𝑾𝑿𝒀𝒁𝒂𝒃𝒄𝒅𝒆𝒇𝒈𝒉𝒊𝒋𝒌𝒍𝒎𝒏𝒐𝒑𝒒𝒓𝒔𝒕𝒖𝒗𝒘𝒙𝒚𝒛0123456789"

SANS_NORMAL = "𝖠𝖡𝖢𝖣𝖤𝖥𝖦𝖧𝖨𝖩𝖪𝖫𝖬𝖭𝖮𝖯𝖰𝖱𝖲𝖳𝖴𝖵𝖶𝖷𝖸𝖹𝖺𝖻𝖼𝖽𝖾𝖿𝗀𝗁𝗂𝗃𝗄𝗅𝗆𝗇𝗈𝗉𝗊𝗋𝗌𝗍𝗎𝗏𝗐𝗑𝗒𝗓𝟢𝟣𝟤𝟥𝟦𝟧𝟨𝟩𝟪𝟫"
SANS_BOLD = "𝗔𝗕𝗖𝗗𝗘𝗙𝗚𝗛𝗜𝗝𝗞𝗟𝗠𝗡𝗢𝗣𝗤𝗥𝗦𝗧𝗨𝗩𝗪𝗫𝗬𝗭𝗮𝗯𝗰𝗱𝗲𝗳𝗴𝗵𝗶𝗷𝗸𝗹𝗺𝗻𝗼𝗽𝗾𝗿𝘀𝘁𝘂𝘃𝘄𝘅𝘆𝘇𝟬𝟭𝟮𝟯𝟰𝟱𝟲𝟳𝟴𝟵"
SANS_ITALIC = "𝘈𝘉𝘊𝘋𝘌𝘍𝘎𝘏𝘐𝘑𝘒𝘓𝘔𝘕𝘖𝘗𝘘𝘙𝘚𝘛𝘜𝘝𝘞𝘟𝘠𝘡𝘢𝘣𝘤𝘥𝘦𝘧𝘨𝘩𝘪𝘫𝘬𝘭𝘮𝘯𝘰𝘱𝘲𝘳𝘴𝘵𝘶𝘷𝘸𝘹𝘺𝘻0123456789"
SANS_BOLD_ITALIC = "𝘼𝘽𝘾𝘿𝙀𝙁𝙂𝙃𝙄𝙅𝙆𝙇𝙈𝙉𝙊𝙋𝙌𝙍𝙎𝙏𝙐𝙑𝙒𝙓𝙔𝙕𝙖𝙗𝙘𝙙𝙚𝙛𝙜𝙝𝙞𝙟𝙠𝙡𝙢𝙣𝙤𝙥𝙦𝙧𝙨𝙩𝙪𝙫𝙬𝙭𝙮𝙯0123456789"

SCRIPT_NORMAL = "𝒜𝐵𝒞𝒟𝐸𝐹𝒢𝐻𝐼𝒥𝒦𝐿𝑀𝒩𝒪𝒫𝒬𝑅𝒮𝒯𝒰𝒱𝒲𝒳𝒴𝒵𝒶𝒷𝒸𝒹𝑒𝒻Z𝒽𝒾𝒿𝓀𝓁𝓂𝓃𝑜𝓅𝓆𝓇𝓈𝓉𝓊𝓋𝓌𝓍𝓎𝓏0123456789"
SCRIPT_BOLD = "𝓐𝓑𝓒𝓓𝓔𝓕𝓖𝓗𝓘𝓙𝓚𝓛𝓜𝓝𝓞𝓟𝓠𝓡𝓢𝓣𝓤𝓥𝓦𝓧𝓨𝓩𝓪𝓫𝓬𝓭𝓮𝓯𝓰𝓱𝓲𝓳𝓴𝓵𝓶𝓷𝓸𝓹𝓺𝓻𝓼𝓽𝓾𝓿𝔀𝔁𝔂𝔃0123456789"

FRAKTUR_NORMAL = "𝔄𝔅ℭ𝔇𝔈𝔉𝔊ℌℑ𝔍𝔎𝔏𝔐𝔑𝔒𝔓𝔔ℜ𝔖𝔗𝔘𝔙𝔚𝔛𝔜ℨ𝔞𝔟𝔠𝔡𝔢𝔣𝔤𝔥𝔦𝔧𝔨𝔩𝔪𝔫𝔬𝔭𝔮𝔯𝔰𝔱𝔲𝔳𝔴𝔵𝔶𝔩0123456789"
FRAKTUR_BOLD = "𝕬𝕭𝕮𝕯𝕰𝕱𝕲𝕳𝕴𝕵𝕶𝕷𝕸𝕹𝕺𝕻𝕼𝕽𝕾𝕿𝖀𝖁𝖂𝖃𝖄𝖅𝖆𝖇𝖈𝖉𝖊𝖋𝖌𝖍𝖎𝖏𝖐𝖑𝖒𝖓𝖔𝖕𝖖𝖗𝖘𝖙𝖚𝖛𝖜𝖝𝖞𝖟0123456789"

DOUBLE_STRUCK = "𝔸𝔹ℂ𝔻𝔼𝔽𝔾ℍ𝕀𝕁𝕂𝕃𝕄ℕ𝕆ℙℚℝ𝕊𝕋𝕌𝕍𝕎𝕏𝕐ℤ𝕒𝕓𝕔𝕕𝕖𝕗𝕘𝕙𝕚𝕛𝕜𝕝𝕞𝕟𝕠𝕡𝕢𝕣𝕤𝕥𝕦𝕧𝕨𝕩𝕪𝕫𝟘𝟙𝟚𝟛𝟜𝟝𝟞𝟟𝟠𝟡"
MONOSPACE = "𝙰𝙱𝙲𝙳𝙴𝙵𝙶𝙷𝙸𝙹𝙺𝙻𝙼𝙽𝙾𝙿𝚀𝚁𝚂𝚃𝚄𝚅𝚆𝚇𝚈𝚉𝚊𝚋𝚌𝚍𝚎𝚏𝚐𝚑𝚒𝚓𝚔𝚕𝚖𝚗𝚘𝚙𝚚𝚛𝚜𝚝𝚞𝚟𝚠𝚡𝚢𝚣𝟶𝟷𝟸𝟹𝟺𝟻𝟼𝟽𝟾𝟿"

SMALL_CAPS_LOWER = "ᴀʙᴄᴅᴇғɢʜɪᴊᴋʟᴍɴᴏᴘǫʀsᴛᴜᴠᴡxʏᴢ"
CIRCLED_ALL = "ⒶⒷⒸⒹⒺⒻⒼⒽⒾⒿⓀⓁⓂⓃⓄⓅⓆⓇⓈⓉⓊⓋⓌⓍⓎⓏⓐⓑⓒⓓⓔⓕⓖⓗⓘⓙⓚⓛⓜⓝⓞⓟⓠⓡⓢⓣⓤⓥⓦⓧⓨⓩ⓪①②③④⑤⑥⑦⑧⑨"
CIRCLED_NEGATIVE = "🅐🅑🅒🅓🅔🅕🅖 Parse error safe fallback"
SQUARED_ALL = "🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉🄰🄱🄲🄳🄴🄵🄶🄷🄸🄹🄺🄻🄼🄽🄾🄿🅀🅁🅂🅃🅄🅅🅆🅇🅈🅉0123456789"
SQUARED_NEGATIVE = "🅰🅱🅲🅳🅴🅵🅶🅷🅸🅹🅺🅻🅼🅽🅾🅿🆀🆁🆂🆃🆄🆅🆆🆇🆈🆉🅰🅱🅲🅳🅴🅵🅶🅷🅸🅹🅺🅻🅼🅽🅾🅿🆀🆁🆂🆃🆄🆅🆆🆇🆈🆉0123456789"
PARENTHESIZED_UPPER = "🄐🄑🄒🄓🄔🄕🄖🄗🄘🄙🄚🄛🄜🄝🄞🄟🄠🄡🄢🄣🄤🄥🄦🄧🄨🄩"
PARENTHESIZED_LOWER = "⒜⒝⒞⒟⒠⒡⒢⒣⒤⒥⒦⒧⒨⒩⒪⒫⒬⒭⒮⒯⒰⒱⒲⒳⒴⒵"
PARENTHESIZED_DIGITS = "⑴⑵⑶⑷⑸⑹⑺⑻⑼"

FULLWIDTH_ALL = "ＡＢＣＤＥＦＧＨＩＪＫＬＭＮＯＰＱＲＳＴＵＶＷＸＹＺａｂｃｄｅｆｇｈｉｊｋｌｍｎｏｐｑｒｓｔｕｖｗｘｙｚ０１２３４５６７８９"

SUBSCRIPT_MAP = {
    "0": "₀",
    "1": "₁",
    "2": "₂",
    "3": "₃",
    "4": "₄",
    "5": "₅",
    "6": "₆",
    "7": "₇",
    "8": "₈",
    "9": "₉",
    "a": "ₐ",
    "e": "ₑ",
    "h": "ₕ",
    "i": "ᵢ",
    "j": "ⱼ",
    "k": "ₖ",
    "l": "ₗ",
    "m": "ₘ",
    "n": "ₙ",
    "o": "ₒ",
    "p": "ₚ",
    "r": "ᵣ",
    "s": "ₛ",
    "t": "ₜ",
    "u": "ᵤ",
    "v": "ᵥ",
    "x": "ₓ",
}

SUPERSCRIPT_MAP = {
    "0": "⁰",
    "1": "¹",
    "2": "²",
    "3": "³",
    "4": "⁴",
    "5": "⁵",
    "6": "⁶",
    "7": "⁷",
    "8": "⁸",
    "9": "⁹",
    "a": "ᵃ",
    "b": "ᵇ",
    "c": "ᶜ",
    "d": "ᵈ",
    "e": "ᵉ",
    "f": "ᶠ",
    "g": "ᵍ",
    "h": "ʰ",
    "i": "ⁱ",
    "j": "ʲ",
    "k": "ᵏ",
    "l": "ˡ",
    "m": "ᵐ",
    "n": "ⁿ",
    "o": "ᵒ",
    "p": "ᵖ",
    "r": "ʳ",
    "s": "ˢ",
    "t": "ᵗ",
    "u": "ᵘ",
    "v": "ᵛ",
    "w": "ʷ",
    "x": "ˣ",
    "y": "ʸ",
    "z": "ᶻ",
    "A": "ᴬ",
    "B": "ᴮ",
    "D": "ᴰ",
    "E": "ᴱ",
    "G": "ᴳ",
    "H": "ᴴ",
    "I": "ᴵ",
    "J": "ᴶ",
    "K": "ᴷ",
    "L": "ᴸ",
    "M": "ᴹ",
    "N": "ᴺ",
    "O": "ᴼ",
    "P": "ᴾ",
    "R": "ᴿ",
    "T": "ᵀ",
    "U": "ᵁ",
    "W": "ᵂ",
}

INVERT_MAP = {
    "a": "ɐ",
    "b": "q",
    "c": "ɔ",
    "d": "p",
    "e": "ǝ",
    "f": "ɟ",
    "g": "ƃ",
    "h": "ɥ",
    "i": "ᴉ",
    "j": "ɾ",
    "k": "ʞ",
    "l": "l",
    "m": "ɯ",
    "n": "u",
    "o": "o",
    "p": "d",
    "q": "b",
    "r": "ɹ",
    "s": "s",
    "t": "ʇ",
    "u": "n",
    "v": "ʌ",
    "w": "ʍ",
    "x": "x",
    "y": "ʎ",
    "z": "z",
    "A": "∀",
    "B": "𐐒",
    "C": "Ɔ",
    "D": "ᗡ",
    "E": "Ǝ",
    "F": "Ⅎ",
    "G": "⅁",
    "H": "H",
    "I": "I",
    "J": "ſ",
    "K": "ʞ",
    "L": "˥",
    "M": "W",
    "N": "N",
    "O": "O",
    "P": "Ԁ",
    "Q": "Ό",
    "R": "ᴚ",
    "S": "S",
    "T": "⊥",
    "U": "∩",
    "V": "Λ",
    "W": "M",
    "X": "X",
    "Y": "⅄",
    "Z": "Z",
    "1": "Ɩ",
    "2": "ᄅ",
    "3": "Ɛ",
    "4": "ㄣ",
    "5": "ϛ",
    "6": "9",
    "7": "ㄥ",
    "8": "8",
    "9": "6",
    "0": "0",
    "?": "¿",
    "!": "¡",
    ".": "˙",
    ",": "'",
    "(": ")",
    ")": "(",
}


def _make_translation_table(source: str, target: str) -> Dict[int, str]:
    return str.maketrans(source, target)


def _apply_char_map(text: str, mapping: Dict[str, str]) -> str:
    return "".join(mapping.get(c, c) for c in text)


def _apply_combining(text: str, char_code: str) -> str:
    return "".join(c + char_code if c.isalnum() else c for c in text)


def _apply_double_combining(text: str, c1: str, c2: str) -> str:
    return "".join(c + c1 + c2 if c.isalnum() else c for c in text)


# Pre-built translation tables
TABLE_SERIF_BOLD = _make_translation_table(ASCII_ALL, SERIF_BOLD)
TABLE_SERIF_ITALIC = _make_translation_table(ASCII_ALL, SERIF_ITALIC)
TABLE_SERIF_BOLD_ITALIC = _make_translation_table(ASCII_ALL, SERIF_BOLD_ITALIC)
TABLE_SANS_NORMAL = _make_translation_table(ASCII_ALL, SANS_NORMAL)
TABLE_SANS_BOLD = _make_translation_table(ASCII_ALL, SANS_BOLD)
TABLE_SANS_ITALIC = _make_translation_table(ASCII_ALL, SANS_ITALIC)
TABLE_SANS_BOLD_ITALIC = _make_translation_table(ASCII_ALL, SANS_BOLD_ITALIC)
TABLE_SCRIPT_NORMAL = _make_translation_table(ASCII_ALL, SCRIPT_NORMAL)
TABLE_SCRIPT_BOLD = _make_translation_table(ASCII_ALL, SCRIPT_BOLD)
TABLE_FRAKTUR_NORMAL = _make_translation_table(ASCII_ALL, FRAKTUR_NORMAL)
TABLE_FRAKTUR_BOLD = _make_translation_table(ASCII_ALL, FRAKTUR_BOLD)
TABLE_DOUBLE_STRUCK = _make_translation_table(ASCII_ALL, DOUBLE_STRUCK)
TABLE_MONOSPACE = _make_translation_table(ASCII_ALL, MONOSPACE)
TABLE_CIRCLED = _make_translation_table(ASCII_ALL, CIRCLED_ALL)
TABLE_FULLWIDTH = _make_translation_table(ASCII_ALL, FULLWIDTH_ALL)
TABLE_SQUARED = _make_translation_table(ASCII_ALL, SQUARED_ALL)
TABLE_SQUARED_NEG = _make_translation_table(ASCII_ALL, SQUARED_NEGATIVE)
TABLE_SMALL_CAPS = _make_translation_table(ASCII_LOWER, SMALL_CAPS_LOWER)


@dataclass(frozen=True)
class FontStyle:
    """Represents a selectable typography style."""

    font_id: int
    name: str
    category: str
    converter: Callable[[str], str]

    def transform(self, text: str) -> str:
        return self.converter(text)


FONTS: List[FontStyle] = []


def _register(font_id: int, name: str, category: str, fn: Callable[[str], str]) -> None:
    FONTS.append(FontStyle(font_id=font_id, name=name, category=category, converter=fn))


# 1 - 20: Mathematical Alphanumeric Core
_register(1, "Serif Bold", "Mathematical", lambda t: t.translate(TABLE_SERIF_BOLD))
_register(2, "Serif Italic", "Mathematical", lambda t: t.translate(TABLE_SERIF_ITALIC))
_register(3, "Serif Bold Italic", "Mathematical", lambda t: t.translate(TABLE_SERIF_BOLD_ITALIC))
_register(4, "Sans-Serif Normal", "Mathematical", lambda t: t.translate(TABLE_SANS_NORMAL))
_register(5, "Sans-Serif Bold", "Mathematical", lambda t: t.translate(TABLE_SANS_BOLD))
_register(6, "Sans-Serif Italic", "Mathematical", lambda t: t.translate(TABLE_SANS_ITALIC))
_register(
    7, "Sans-Serif Bold Italic", "Mathematical", lambda t: t.translate(TABLE_SANS_BOLD_ITALIC)
)
_register(8, "Script Normal", "Script", lambda t: t.translate(TABLE_SCRIPT_NORMAL))
_register(9, "Script Bold", "Script", lambda t: t.translate(TABLE_SCRIPT_BOLD))
_register(10, "Fraktur Normal", "Gothic", lambda t: t.translate(TABLE_FRAKTUR_NORMAL))
_register(11, "Fraktur Bold", "Gothic", lambda t: t.translate(TABLE_FRAKTUR_BOLD))
_register(12, "Double Struck", "Blackboard", lambda t: t.translate(TABLE_DOUBLE_STRUCK))
_register(13, "Monospace", "Monospace", lambda t: t.translate(TABLE_MONOSPACE))
_register(14, "Circled", "Enclosed", lambda t: t.translate(TABLE_CIRCLED))
_register(15, "Squared", "Enclosed", lambda t: t.translate(TABLE_SQUARED))
_register(16, "Squared Negative", "Enclosed", lambda t: t.translate(TABLE_SQUARED_NEG))
_register(17, "Fullwidth Aesthetic", "Wide", lambda t: t.translate(TABLE_FULLWIDTH))
_register(18, "Small Capitals", "Typography", lambda t: t.lower().translate(TABLE_SMALL_CAPS))
_register(19, "Subscript", "Phonetic", lambda t: _apply_char_map(t, SUBSCRIPT_MAP))
_register(20, "Superscript", "Phonetic", lambda t: _apply_char_map(t, SUPERSCRIPT_MAP))

# 21 - 35: Inverted, Spaced, and Case Stylings
_register(
    21, "Upside Down", "Transform", lambda t: "".join(INVERT_MAP.get(c, c) for c in reversed(t))
)
_register(22, "Wide Spaced", "Transform", lambda t: " ".join(list(t)))
_register(23, "Double Spaced", "Transform", lambda t: "  ".join(list(t)))
_register(
    24,
    "Alternating Case",
    "Transform",
    lambda t: "".join(c.upper() if i % 2 == 0 else c.lower() for i, c in enumerate(t)),
)
_register(25, "Inverted Case", "Transform", lambda t: t.swapcase())
_register(26, "Hyphenated Spacing", "Transform", lambda t: "-".join(list(t.replace(" ", ""))))
_register(27, "Dotted Spacing", "Transform", lambda t: ".".join(list(t.replace(" ", ""))))
_register(28, "Slash Spacing", "Transform", lambda t: "/".join(list(t.replace(" ", ""))))
_register(29, "Reverse Text", "Transform", lambda t: t[::-1])
_register(
    30, "Monospace Spaced", "Monospace", lambda t: " ".join(list(t.translate(TABLE_MONOSPACE)))
)
_register(
    31,
    "Small Caps Spaced",
    "Typography",
    lambda t: " ".join(list(t.lower().translate(TABLE_SMALL_CAPS))),
)
_register(
    32, "Sans Bold Spaced", "Mathematical", lambda t: " ".join(list(t.translate(TABLE_SANS_BOLD)))
)
_register(
    33,
    "Serif Bold Spaced",
    "Mathematical",
    lambda t: " ".join(list(t.translate(TABLE_SERIF_BOLD))),
)
_register(
    34,
    "Double Struck Spaced",
    "Blackboard",
    lambda t: " ".join(list(t.translate(TABLE_DOUBLE_STRUCK))),
)
_register(35, "Fullwidth Spaced", "Wide", lambda t: " ".join(list(t.translate(TABLE_FULLWIDTH))))

# 36 - 60: Combining Diacritical Marks & Overlays
_register(36, "Strikethrough Single", "Overlay", lambda t: _apply_combining(t, "\u0336"))
_register(37, "Tilde Strike", "Overlay", lambda t: _apply_combining(t, "\u0334"))
_register(38, "Slash Through", "Overlay", lambda t: _apply_combining(t, "\u0337"))
_register(39, "Underline Single", "Overlay", lambda t: _apply_combining(t, "\u0332"))
_register(40, "Underline Double", "Overlay", lambda t: _apply_combining(t, "\u0333"))
_register(41, "Overline Single", "Overlay", lambda t: _apply_combining(t, "\u0305"))
_register(42, "Overline Double", "Overlay", lambda t: _apply_combining(t, "\u033f"))
_register(
    43, "Overline & Underline", "Overlay", lambda t: _apply_double_combining(t, "\u0305", "\u0332")
)
_register(44, "Dotted Above", "Overlay", lambda t: _apply_combining(t, "\u0307"))
_register(45, "Dotted Below", "Overlay", lambda t: _apply_combining(t, "\u0323"))
_register(46, "Double Dot Above", "Overlay", lambda t: _apply_combining(t, "\u0308"))
_register(47, "Ring Above", "Overlay", lambda t: _apply_combining(t, "\u030a"))
_register(48, "Caron Above", "Overlay", lambda t: _apply_combining(t, "\u030c"))
_register(49, "Acute Above", "Overlay", lambda t: _apply_combining(t, "\u0301"))
_register(50, "Grave Above", "Overlay", lambda t: _apply_combining(t, "\u0300"))
_register(51, "Breve Above", "Overlay", lambda t: _apply_combining(t, "\u0306"))
_register(52, "Inverted Breve Below", "Overlay", lambda t: _apply_combining(t, "\u032f"))
_register(53, "Cross Below", "Overlay", lambda t: _apply_combining(t, "\u0353"))
_register(54, "Arrow Below", "Overlay", lambda t: _apply_combining(t, "\u034e"))
_register(55, "Harpoon Below", "Overlay", lambda t: _apply_combining(t, "\u035c"))
_register(56, "Seagull Below", "Overlay", lambda t: _apply_combining(t, "\u033c"))
_register(57, "Ogonek Hook", "Overlay", lambda t: _apply_combining(t, "\u0328"))
_register(58, "Cedilla Hook", "Overlay", lambda t: _apply_combining(t, "\u0327"))
_register(59, "Bridge Above", "Overlay", lambda t: _apply_combining(t, "\u0346"))
_register(60, "Tilde Above", "Overlay", lambda t: _apply_combining(t, "\u0303"))

# 61 - 85: Hybrid Combinations (Font + Overlay)
_register(
    61,
    "Serif Bold Underline",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_SERIF_BOLD), "\u0332"),
)
_register(
    62,
    "Serif Bold Strike",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_SERIF_BOLD), "\u0336"),
)
_register(
    63,
    "Serif Bold Overline",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_SERIF_BOLD), "\u0305"),
)
_register(
    64,
    "Sans Bold Underline",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_SANS_BOLD), "\u0332"),
)
_register(
    65,
    "Sans Bold Strike",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_SANS_BOLD), "\u0336"),
)
_register(
    66,
    "Sans Bold Overline",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_SANS_BOLD), "\u0305"),
)
_register(
    67,
    "Monospace Underline",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_MONOSPACE), "\u0332"),
)
_register(
    68,
    "Monospace Strike",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_MONOSPACE), "\u0336"),
)
_register(
    69,
    "Monospace Overline",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_MONOSPACE), "\u0305"),
)
_register(
    70,
    "Script Bold Underline",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_SCRIPT_BOLD), "\u0332"),
)
_register(
    71,
    "Script Bold Strike",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_SCRIPT_BOLD), "\u0336"),
)
_register(
    72,
    "Fraktur Bold Underline",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_FRAKTUR_BOLD), "\u0332"),
)
_register(
    73,
    "Fraktur Bold Strike",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_FRAKTUR_BOLD), "\u0336"),
)
_register(
    74,
    "Double Struck Underline",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_DOUBLE_STRUCK), "\u0332"),
)
_register(
    75,
    "Double Struck Strike",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_DOUBLE_STRUCK), "\u0336"),
)
_register(
    76,
    "Small Caps Underline",
    "Hybrid",
    lambda t: _apply_combining(t.lower().translate(TABLE_SMALL_CAPS), "\u0332"),
)
_register(
    77,
    "Small Caps Strike",
    "Hybrid",
    lambda t: _apply_combining(t.lower().translate(TABLE_SMALL_CAPS), "\u0336"),
)
_register(
    78,
    "Fullwidth Underline",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_FULLWIDTH), "\u0332"),
)
_register(
    79,
    "Fullwidth Strike",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_FULLWIDTH), "\u0336"),
)
_register(
    80,
    "Serif Italic Underline",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_SERIF_ITALIC), "\u0332"),
)
_register(
    81,
    "Serif Italic Strike",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_SERIF_ITALIC), "\u0336"),
)
_register(
    82,
    "Sans Italic Underline",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_SANS_ITALIC), "\u0332"),
)
_register(
    83,
    "Sans Italic Strike",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_SANS_ITALIC), "\u0336"),
)
_register(
    84,
    "Circled Underline",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_CIRCLED), "\u0332"),
)
_register(
    85,
    "Circled Strike",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_CIRCLED), "\u0336"),
)

# 86 - 105: Exotic, Symbolic, and Aesthetic Typography
_register(
    86,
    "Serif Bold Double Underline",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_SERIF_BOLD), "\u0333"),
)
_register(
    87,
    "Sans Bold Double Underline",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_SANS_BOLD), "\u0333"),
)
_register(
    88,
    "Monospace Double Underline",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_MONOSPACE), "\u0333"),
)
_register(
    89,
    "Double Struck Double Underline",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_DOUBLE_STRUCK), "\u0333"),
)
_register(
    90,
    "Small Caps Double Underline",
    "Hybrid",
    lambda t: _apply_combining(t.lower().translate(TABLE_SMALL_CAPS), "\u0333"),
)
_register(
    91,
    "Sans Bold Dot Above",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_SANS_BOLD), "\u0307"),
)
_register(
    92,
    "Monospace Dot Above",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_MONOSPACE), "\u0307"),
)
_register(
    93,
    "Serif Bold Dot Above",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_SERIF_BOLD), "\u0307"),
)
_register(
    94,
    "Sans Bold Ring Above",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_SANS_BOLD), "\u030a"),
)
_register(
    95,
    "Monospace Ring Above",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_MONOSPACE), "\u030a"),
)
_register(
    96,
    "Sans Bold Cross Below",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_SANS_BOLD), "\u0353"),
)
_register(
    97,
    "Monospace Cross Below",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_MONOSPACE), "\u0353"),
)
_register(
    98,
    "Double Struck Cross Below",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_DOUBLE_STRUCK), "\u0353"),
)
_register(
    99,
    "Small Caps Cross Below",
    "Hybrid",
    lambda t: _apply_combining(t.lower().translate(TABLE_SMALL_CAPS), "\u0353"),
)
_register(
    100,
    "Serif Bold Tilde Strike",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_SERIF_BOLD), "\u0334"),
)
_register(
    101,
    "Sans Bold Tilde Strike",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_SANS_BOLD), "\u0334"),
)
_register(
    102,
    "Monospace Tilde Strike",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_MONOSPACE), "\u0334"),
)
_register(
    103,
    "Double Struck Tilde Strike",
    "Hybrid",
    lambda t: _apply_combining(t.translate(TABLE_DOUBLE_STRUCK), "\u0334"),
)
_register(
    104,
    "Parenthesized",
    "Enclosed",
    lambda t: t.translate(_make_translation_table(ASCII_LOWER, PARENTHESIZED_LOWER)),
)
_register(
    105,
    "Small Caps Box Framing",
    "Typography",
    lambda t: f"[{t.lower().translate(TABLE_SMALL_CAPS)}]",
)


def get_font(font_id: int) -> Optional[FontStyle]:
    """Retrieves a font style by its 1-based index."""
    if 1 <= font_id <= len(FONTS):
        return FONTS[font_id - 1]
    return None


def get_all_fonts() -> List[FontStyle]:
    """Returns the complete list of available font styles."""
    return FONTS


def format_font_page(page_number: int, per_page: int = 10, sample_text: str = "general") -> str:
    """Renders a text page displaying font samples for selection."""
    total = len(FONTS)
    total_pages = (total + per_page - 1) // per_page
    current_page = max(1, min(page_number, total_pages))

    start = (current_page - 1) * per_page
    end = min(start + per_page, total)

    lines = [
        f"--- Available Fonts (Page {current_page}/{total_pages}) ---",
        "Type font number to select, or 'next' / 'prev' to browse:\n",
    ]

    for font in FONTS[start:end]:
        preview = font.transform(sample_text)
        lines.append(f"[{font.font_id:3d}] {font.name:<28} : {preview}")

    lines.append(f"\nShowing {start + 1}-{end} of {total} fonts.")
    return "\n".join(lines)
