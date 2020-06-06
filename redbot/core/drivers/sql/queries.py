from typing import Final

_create_table: Final[
    str
] = """
CREATE TABLE IF NOT EXISTS {table_name} (
    data JSON,
);
"""

