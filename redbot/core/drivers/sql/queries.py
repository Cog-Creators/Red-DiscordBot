from typing import Final

_create_table: Final[
    str
] = """
CREATE TABLE IF NOT EXISTS {table_name} (
    data JSON
);
"""

_get_query: Final[
    str
] = """
SELECT json_extract(target_table.data, :path)
FROM {table_name} as target_table
"""
_get_type_query: Final[
    str
] = """
SELECT json_type(target_table.data, :path)
FROM {table_name} as target_table
"""

_set_query: Final[
    str
] = """
UPDATE {table_name}
  set data = json_set(data, :path, json(:value))
"""

_clear_query: Final[
    str
] = """
UPDATE {table_name}
  set data = json_remove(data, :path)
"""

_prep_query: Final[
    str
] = """
INSERT INTO {table_name} (data)
SELECT '{{}}'
WHERE NOT EXISTS (SELECT * FROM {table_name})
"""
