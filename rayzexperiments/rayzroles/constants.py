"""Constants and configuration defaults for RayzRoles."""

from typing import Final

WIZARD_TIMEOUT_SECONDS: Final[float] = 60.0
ENTRY_TIMEOUT_SECONDS: Final[float] = 120.0
MAX_DESCRIPTION_LENGTH: Final[int] = 4000

CONFIG_IDENTIFIER: Final[int] = 893475928374
GLOBAL_KEY_MENUS: Final[str] = "menus"

PROMPT_INITIAL_TITLE: Final[str] = "Role Setup Wizard"
PROMPT_INITIAL_DESC: Final[str] = (
    "Setting up self-assignable roles for channel: {channel}\n\n"
    "Generate self roles? [y/n]\n"
    "Type 'y' to continue or 'n' to cancel."
)

PROMPT_CANCELLED: Final[str] = "Ok, that is it."
PROMPT_TIMEOUT: Final[str] = "Setup timed out. Please run the command again when ready."
PROMPT_INVALID_CHOICE: Final[str] = "Invalid choice. Setup cancelled."

PROMPT_ROLE_TITLE: Final[str] = "Add Role ({ordinal})"
PROMPT_ROLE_DESC: Final[str] = (
    "Send your {ordinal} emoji with tagged role:\n"
    "- Existing role: <emoji> @Role\n"
    "- Create new role: <emoji> cr <rolename>\n\n"
    "Type 'cancel' to exit setup."
)

PROMPT_ADD_ANOTHER_TITLE: Final[str] = "Add Another Role"
PROMPT_ADD_ANOTHER_DESC: Final[str] = (
    "Current roles configured: {count}\n\n" "Add another one? [y/n]"
)

MENU_EMBED_TITLE: Final[str] = "Self-Assignable Roles"
MENU_EMBED_FOOTER: Final[str] = "React to toggle your role."
