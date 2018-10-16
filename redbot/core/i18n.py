import contextlib
import os
import re
import weakref
import sys
from pathlib import Path
from typing import Callable, Union, Set, Optional, TextIO

__all__ = ["get_locale", "set_locale", "Translator"]

PY_36 = sys.version_info < (3, 7, 0)


WAITING_FOR_MSGID = 1
IN_MSGID = 2
WAITING_FOR_MSGSTR = 3
IN_MSGSTR = 4

MSGID = 'msgid "'
MSGSTR = 'msgstr "'


_translators: Set["Translator"] = weakref.WeakSet()


if PY_36:
    _current_locale = "en-US"

    def get_locale():
        return _current_locale

    def set_locale(locale):
        global _current_locale
        _current_locale = locale
        _reload_locales()

    def _reload_locales():
        for translator in _translators:
            translator.load_translations()


else:
    import contextvars

    _current_locales: Set[str] = set()
    _locale_var: contextvars.ContextVar[str] = contextvars.ContextVar(
        "Locale", default="en-US"
    )

    def get_locale() -> str:
        return _locale_var.get()

    def set_locale(locale: str) -> None:
        if locale not in _current_locales:
            _load_locale(locale)
        _locale_var.set(locale)

    def _load_locale(locale: str) -> None:
        _current_locales.add(locale)
        for translator in _translators:
            translator.load_translations(locale)


def _parse(translation_file):
    """
    Custom gettext parsing of translation files. All credit for this code goes
    to ProgVal/Valentin Lorentz and the Limnoria project.

    https://github.com/ProgVal/Limnoria/blob/master/src/i18n.py

    :param translation_file:
        An open file-like object containing translations.
    :return:
        A set of 2-tuples containing the original string and the translated version.
    """
    step = WAITING_FOR_MSGID
    translations = set()
    untranslated = ""
    translated = ""
    for line in translation_file:
        line = line[0:-1]  # Remove the ending \n
        line = line

        if line.startswith(MSGID):
            # Don't check if step is WAITING_FOR_MSGID
            untranslated = ""
            translated = ""
            data = line[len(MSGID) : -1]
            if len(data) == 0:  # Multiline mode
                step = IN_MSGID
            else:
                untranslated += data
                step = WAITING_FOR_MSGSTR

        elif step is IN_MSGID and line.startswith('"') and line.endswith('"'):
            untranslated += line[1:-1]
        elif step is IN_MSGID and untranslated == "":  # Empty MSGID
            step = WAITING_FOR_MSGID
        elif step is IN_MSGID:  # the MSGID is finished
            step = WAITING_FOR_MSGSTR

        if step is WAITING_FOR_MSGSTR and line.startswith(MSGSTR):
            data = line[len(MSGSTR) : -1]
            if len(data) == 0:  # Multiline mode
                step = IN_MSGSTR
            else:
                translations |= {(untranslated, data)}
                step = WAITING_FOR_MSGID

        elif step is IN_MSGSTR and line.startswith('"') and line.endswith('"'):
            translated += line[1:-1]
        elif step is IN_MSGSTR:  # the MSGSTR is finished
            step = WAITING_FOR_MSGID
            if translated == "":
                translated = untranslated
            translations |= {(untranslated, translated)}
    if step is IN_MSGSTR:
        if translated == "":
            translated = untranslated
        translations |= {(untranslated, translated)}
    return translations


def _normalize(string, remove_newline=False):
    """
    String normalization.

    All credit for this code goes
    to ProgVal/Valentin Lorentz and the Limnoria project.

    https://github.com/ProgVal/Limnoria/blob/master/src/i18n.py

    :param string:
    :param remove_newline:
    :return:
    """

    def normalize_whitespace(s):
        """Normalizes the whitespace in a string; \s+ becomes one space."""
        if not s:
            return str(s)  # not the same reference
        starts_with_space = s[0] in " \n\t\r"
        ends_with_space = s[-1] in " \n\t\r"
        if remove_newline:
            newline_re = re.compile("[\r\n]+")
            s = " ".join(filter(None, newline_re.split(s)))
        s = " ".join(filter(None, s.split("\t")))
        s = " ".join(filter(None, s.split(" ")))
        if starts_with_space:
            s = " " + s
        if ends_with_space:
            s += " "
        return s

    if string is None:
        return ""

    string = string.replace("\\n\\n", "\n\n")
    string = string.replace("\\n", " ")
    string = string.replace('\\"', '"')
    string = string.replace("'", "'")
    string = normalize_whitespace(string)
    string = string.strip("\n")
    string = string.strip("\t")
    return string


class Translator(Callable[[str], str]):
    """Class for Red's custom gettext function.

    Parameters
    ----------
    file_location : `str` or `pathlib.Path`
        This should always be ``__file__`` otherwise your localizations
        will not load.

    """

    def __init__(self, file_location: Union[str, Path, os.PathLike]):
        self.cog_folder = Path(file_location).resolve().parent
        self.translations = {}

        _translators.add(self)

        self.load_translations()

    @property
    def locale_folder(self) -> Path:
        return self.cog_folder / "locales"

    def get_catalog_path(self, locale: str) -> Path:
        return self.locale_folder / f"{locale}.po"

    def __call__(self, untranslated: str) -> str:
        """Translate the given string.

        This will look for the string in the translator's :code:`.pot` file,
        with respect to the current locale.
        """
        try:
            return self.translations[get_locale()][_normalize(untranslated, True)]
        except KeyError:
            return untranslated

    def load_translations(self, locale: Optional[str] = None) -> None:
        """
        Loads the current translations.
        """
        if locale is not None or PY_36:
            self._load_locale(locale)
        else:
            for _locale in _current_locales:
                self._load_locale(_locale)

    def _load_locale(self, locale: str) -> None:
        if PY_36:
            # There can only be one locale at a time on 3.6
            self.translations = {}
        self.translations[locale] = {}
        path = self.get_catalog_path(locale)
        with contextlib.suppress(FileNotFoundError), path.open(encoding="utf-8") as file:
            self._parse(file, locale=locale)

    def _parse(self, translation_file: TextIO, locale: str) -> None:
        for translation in _parse(translation_file):
            self._add_translation(locale, *translation)

    def _add_translation(self, locale: str, untranslated: str, translated: str):
        untranslated = _normalize(untranslated, True)
        translated = _normalize(translated)
        if translated:
            self.translations[locale][untranslated] = translated
