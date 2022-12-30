import itertools
import re
from typing import Any, NoReturn

from schema import And, Const, Optional, Schema, SchemaError, Use

from redbot.core.i18n import Translator

__all__ = ("TRIVIA_LIST_SCHEMA", "format_schema_error")

T_ = Translator("Trivia", __file__)
KEY_ERROR_MSG_RE = re.compile(r"Key '(.+)' error:")


class SchemaErrorMessage(str):
    def format(self, *args: Any, **kwargs: Any) -> str:
        return T_(str(self))


def int_or_float(value: Any) -> float:
    if not isinstance(value, (float, int)):
        raise TypeError("Value needs to be an integer or a float.")
    return float(value)


_ = SchemaErrorMessage
TRIVIA_LIST_SCHEMA = Schema(
    {
        Optional("AUTHOR"): And(str, error=_("{key} key must be a text value.")),
        Optional("CONFIG"): And(
            {
                Optional("max_score"): And(
                    int,
                    lambda n: n >= 1,
                    error=_("{key} key in {parent_key} must be a positive integer."),
                ),
                Optional("timeout"): And(
                    Use(int_or_float),
                    lambda n: n > 0.0,
                    error=_("{key} key in {parent_key} must be a positive number."),
                ),
                Optional("delay"): And(
                    Use(int_or_float),
                    lambda n: n >= 4.0,
                    error=_(
                        "{key} key in {parent_key} must be a positive number"
                        " greater than or equal to 4."
                    ),
                ),
                Optional("bot_plays"): Const(
                    bool, error=_("{key} key in {parent_key} must be either true or false.")
                ),
                Optional("reveal_answer"): Const(
                    bool, error=_("{key} key in {parent_key} must be either true or false.")
                ),
                Optional("payout_multiplier"): And(
                    Use(int_or_float),
                    lambda n: n >= 0.0,
                    error=_("{key} key in {parent_key} must be a non-negative number."),
                ),
                Optional("use_spoilers"): Const(
                    bool, error=_("{key} key in {parent_key} must be either true or false.")
                ),
            },
            error=_("{key} should be a 'key: value' mapping."),
        ),
        str: And(
            [str, int, bool, float],
            error=_("Value of question {key} is not a list of text values (answers)."),
        ),
    },
    error=_("A trivia list should be a 'key: value' mapping."),
)


def format_schema_error(exc: SchemaError) -> str:
    # dict.fromkeys is used for de-duplication with order preservation
    errors = {idx: msg for idx, msg in enumerate(exc.errors) if msg is not None}
    if not errors:
        return str(exc)
    error_idx, error_msg_fmt = errors.popitem()

    autos = dict.fromkeys(msg for msg in itertools.islice(exc.autos, error_idx) if msg is not None)
    keys = [match[1] for msg in autos if (match := KEY_ERROR_MSG_RE.fullmatch(msg)) is not None]
    key_count = len(keys)
    if key_count == 2:
        key = keys[-1]
        parent_key = keys[-2]
    elif key_count == 1:
        key = keys[-1]
        # should only happen for messages where this field isn't used
        parent_key = "UNKNOWN"
    else:
        # should only happen for messages where neither of the fields are used
        key = parent_key = "UNKNOWN"

    return error_msg_fmt.format(key=repr(key), parent_key=repr(parent_key))
