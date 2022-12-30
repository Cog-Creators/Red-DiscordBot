from schema import And, Const, Or, Optional, Schema

__all__ = ("TRIVIA_LIST_SCHEMA")


TRIVIA_LIST_SCHEMA = Schema(
    {
        Optional("AUTHOR"): str,
        Optional("CONFIG"): {
            Optional("max_score"): And(
                int, lambda n: n >= 1, error="max_score must be a positive integer",
            ),
            Optional("timeout"): And(
                Or(int, float),
                lambda n: n > 0.0,
                error="timeout must be a positive number",
            ),
            Optional("delay"): And(
                Or(int, float),
                lambda n: n >= 4.0,
                error="delay must be a positive number greater than or equal to 4",
            ),
            Optional("bot_plays"): Const(bool, error="bot_plays must be either true or false"),
            Optional("reveal_answer"): Const(
                bool, error="reveal_answer must be either true or false"
            ),
            Optional("payout_multiplier"): And(
                Or(int, float),
                lambda n: n >= 0.0,
                error="payout_multiplier must be a non-negative number",
            ),
            Optional("use_spoilers"): Const(
                bool, error="use_spoilers must be either true or false"
            ),
        },
        str: [str, int, bool, float],
    },
)
