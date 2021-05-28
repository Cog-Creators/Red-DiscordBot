from json import JSONDecoder as JSONDecoder
from json import JSONDecodeError as JSONDecodeError
from json import JSONEncoder as JSONEncoder

from . import mujson

__all__ = [
    "dump",
    "dumps",
    "load",
    "loads",
    "JSONDecoder",
    "JSONDecodeError",
    "JSONEncoder",
    "overload_stdlib",
    "restore_stdlib",
]

FAST_JSON_LIBS_DUMP = ["rapidjson", "ujson", "yajl"]
FAST_JSON_LIBS_DUMPS = ["orjson", "mjson", "rapidjson", "ujson", "yajl"]
FAST_JSON_LIBS_LOAD = ["ujson", "simplejson", "rapidjson"]
FAST_JSON_LIBS_LOADS = ["orjson", "ujson", "simplejson", "rapidjson"]

dump = mujson.mujson_function("dump", ranking=FAST_JSON_LIBS_DUMP)
dumps = mujson.mujson_function("dumps", ranking=FAST_JSON_LIBS_DUMPS)
load = mujson.mujson_function("load", ranking=FAST_JSON_LIBS_LOAD)
loads = mujson.mujson_function("loads", ranking=FAST_JSON_LIBS_LOADS)
backup_dumps, backup_dump, backup_loads, backup_load = None, None, None, None


def overload_stdlib():
    global backup_dumps, backup_dump, backup_loads, backup_load
    import json

    if not backup_dumps and json.dumps is not dumps:
        backup_dumps = json.dumps
        backup_dump = json.dump
        backup_loads = json.loads
        backup_load = json.load
    if json.dumps is not dumps:
        json.loads = loads
        json.load = load
        json.dumps = dumps
        json.dump = dump


def restore_stdlib():
    import json

    if backup_dumps and json.dumps is dumps:
        json.loads = backup_loads
        json.load = backup_load
        json.dumps = backup_dumps
        json.dump = backup_dump
