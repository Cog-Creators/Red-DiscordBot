"""Constants and configuration defaults for RayzCServe."""

from typing import Final

CONFIG_IDENTIFIER: Final[int] = 928374829103
GLOBAL_KEY_SNAPSHOTS: Final[str] = "snapshots"

WIZARD_TIMEOUT_SECONDS: Final[float] = 90.0
RENAMING_DELAY_SECONDS: Final[float] = 1.2
FONTS_PER_PAGE: Final[int] = 10
MAX_DISCORD_NAME_LENGTH: Final[int] = 100

PROMPT_INITIAL_TITLE: Final[str] = "RayzCServe Typography Wizard"
PROMPT_INITIAL_DESC: Final[str] = (
    "Server-wide typography and styling manager.\n\n"
    "This wizard will guide you through selecting from over 100 fonts, "
    "configuring symbols or borders, and applying uniform styling across "
    "channels, categories, and roles.\n\n"
    "Proceed with setup? [y/n]\n"
    "Type 'y' to continue or 'n' to cancel."
)

PROMPT_CANCELLED: Final[str] = "Setup cancelled. No changes have been applied."
PROMPT_TIMEOUT: Final[str] = "Setup timed out due to inactivity."
PROMPT_UNDO_SUCCESS: Final[
    str
] = "Successfully restored previous server element names from backup."
PROMPT_UNDO_NONE: Final[str] = "No backup snapshot found for this server."
