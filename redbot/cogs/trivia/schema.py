from schema import And, Const, Optional, Schema, Use

__all__ = ("TRIVIA_LIST_SCHEMA")


def int_or_float(value: Any) -> float:
    if not isinstance(value, (float, int)):
        raise TypeError("Value needs to be an integer or a float.")
    return float(value)


TRIVIA_LIST_SCHEMA = Schema(
    {
        Optional("AUTHOR"): And(str, error="'AUTHOR' key must be a text value."),
        Optional("CONFIG"): {
            Optional("max_score"): And(
                int, lambda n: n >= 1, error="'max_score' must be a positive integer",
            ),
            Optional("timeout"): And(
                Use(int_or_float),
                lambda n: n > 0.0,
                error="'timeout' must be a positive number",
            ),
            Optional("delay"): And(
                Use(int_or_float),
                lambda n: n >= 4.0,
                error="'delay' must be a positive number greater than or equal to 4",
            ),
            Optional("bot_plays"): Const(bool, error="'bot_plays' must be either true or false"),
            Optional("reveal_answer"): Const(
                bool, error="'reveal_answer' must be either true or false"
            ),
            Optional("payout_multiplier"): And(
                Use(int_or_float),
                lambda n: n >= 0.0,
                error="'payout_multiplier' must be a non-negative number",
            ),
            Optional("use_spoilers"): Const(
                bool, error="'use_spoilers' must be either true or false"
            ),
        },
        str: [str, int, bool, float],
    },
)
