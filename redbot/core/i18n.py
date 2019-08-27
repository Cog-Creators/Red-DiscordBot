import contextlib
import functools
import io
import os
from pathlib import Path
from typing import Callable, Union, Dict, Optional

import babel.localedata
from babel.core import Locale

__all__ = [
    "get_locale",
    "set_locale",
    "reload_locales",
    "cog_i18n",
    "Translator",
    "get_babel_locale",
]

_current_locale = "en-US"

WAITING_FOR_MSGID = 1
IN_MSGID = 2
WAITING_FOR_MSGSTR = 3
IN_MSGSTR = 4

MSGID = 'msgid "'
MSGSTR = 'msgstr "'

_translators = []


def get_locale():
    return _current_locale


def set_locale(locale):
    global _current_locale
    _current_locale = locale
    reload_locales()


def reload_locales():
    for translator in _translators:
        translator.load_translations()


def _parse(translation_file: io.TextIOWrapper) -> Dict[str, str]:
    """
    Custom gettext parsing of translation files.

    Parameters
    ----------
    translation_file : io.TextIOWrapper
        An open text file containing translations.

    Returns
    -------
    Dict[str, str]
        A dict mapping the original strings to their translations. Empty
        translated strings are omitted.

    """
    step = None
    untranslated = ""
    translated = ""
    translations = {}
    for line in translation_file:
        line = line.strip()

        if line.startswith(MSGID):
            # New msgid
            if step is IN_MSGSTR and translated:
                # Store the last translation
                translations[_unescape(untranslated)] = _unescape(translated)
            step = IN_MSGID
            untranslated = line[len(MSGID) : -1]
        elif line.startswith('"') and line.endswith('"'):
            if step is IN_MSGID:
                # Line continuing on from msgid
                untranslated += line[1:-1]
            elif step is IN_MSGSTR:
                # Line continuing on from msgstr
                translated += line[1:-1]
        elif line.startswith(MSGSTR):
            # New msgstr
            step = IN_MSGSTR
            translated = line[len(MSGSTR) : -1]

    if step is IN_MSGSTR and translated:
        # Store the final translation
        translations[_unescape(untranslated)] = _unescape(translated)
    return translations


def _unescape(string):
    string = string.replace(r"\\", "\\")
    string = string.replace(r"\t", "\t")
    string = string.replace(r"\r", "\r")
    string = string.replace(r"\n", "\n")
    string = string.replace(r"\"", '"')
    return string


def get_locale_path(cog_folder: Path, extension: str) -> Path:
    """
    Gets the folder path containing localization files.

    :param Path cog_folder:
        The cog folder that we want localizations for.
    :param str extension:
        Extension of localization files.
    :return:
        Path of possible localization file, it may not exist.
    """
    return cog_folder / "locales" / "{}.{}".format(get_locale(), extension)


class Translator(Callable[[str], str]):
    """Function to get translated strings at runtime."""

    def __init__(self, name: str, file_location: Union[str, Path, os.PathLike]):
        """
        Initializes an internationalization object.

        Parameters
        ----------
        name : str
            Your cog name.
        file_location : `str` or `pathlib.Path`
            This should always be ``__file__`` otherwise your localizations
            will not load.

        """
        self.cog_folder = Path(file_location).resolve().parent
        self.cog_name = name
        self.translations = {}

        _translators.append(self)

        self.load_translations()

    def __call__(self, untranslated: str) -> str:
        """Translate the given string.

        This will look for the string in the translator's :code:`.pot` file,
        with respect to the current locale.
        """
        try:
            return self.translations[untranslated]
        except KeyError:
            return untranslated

    def load_translations(self):
        """
        Loads the current translations.
        """
        self.translations = {}
        locale_path = get_locale_path(self.cog_folder, "po")
        with contextlib.suppress(IOError, FileNotFoundError):
            with locale_path.open(encoding="utf-8") as file:
                self._parse(file)

    def _parse(self, translation_file):
        self.translations.update(_parse(translation_file))

    def _add_translation(self, untranslated, translated):
        untranslated = _unescape(untranslated)
        translated = _unescape(translated)
        if translated:
            self.translations[untranslated] = translated


@functools.lru_cache()
def _get_babel_locale(red_locale: str) -> babel.core.Locale:
    supported_locales = babel.localedata.locale_identifiers()
    try:  # Handles cases where red_locale is already Babel supported
        babel_locale = Locale(*babel.parse_locale(red_locale))
    except (ValueError, babel.core.UnknownLocaleError):
        try:
            babel_locale = Locale(*babel.parse_locale(red_locale, sep="-"))
        except (ValueError, babel.core.UnknownLocaleError):
            # ValueError is Raised by `parse_locale` when an invalid Locale is given to it
            # Lets handle it silently and default to "en_US"
            try:
                # Try to find a babel locale that's close to the one used by red
                babel_locale = Locale(Locale.negotiate([red_locale], supported_locales, sep="-"))
            except (ValueError, TypeError, babel.core.UnknownLocaleError):
                # If we fail to get a close match we will then default to "en_US"
                babel_locale = Locale("en", "US")
    return babel_locale


def get_babel_locale(locale: Optional[str] = None) -> babel.core.Locale:
    """Function to get a ``babel.core.Locale`` for specified locale or the bots locale.

    Parameters
    ----------
    locale : : Optional[str]
    The locale to get, if ``None`` is specified it defaults to the bot's locale.

    Returns
    -------
    babel.core.Locale
        The babel locale object.
    """
    if locale is None:
        locale = get_locale()
    return _get_babel_locale(locale)


# This import to be down here to avoid circular import issues.
# This will be cleaned up at a later date
# noinspection PyPep8
from . import commands


def cog_i18n(translator: Translator):
    """Get a class decorator to link the translator to this cog."""

    def decorator(cog_class: type):
        cog_class.__translator__ = translator
        for name, attr in cog_class.__dict__.items():
            if isinstance(attr, (commands.Group, commands.Command)):
                attr.translator = translator
                setattr(cog_class, name, attr)
        return cog_class

    return decorator
