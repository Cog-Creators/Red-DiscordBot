import contextlib
import importlib
import json as stblib_json
from json import JSONDecoder as JSONDecoder
from json import JSONDecodeError as JSONDecodeError
from json import JSONEncoder as JSONEncoder

MODULES = ("orjson", "ujson")
mainjson = None


__all__ = [
    "dump",
    "dumps",
    "load",
    "loads",
    "json_module",
    "JSONDecoder",
    "JSONDecodeError",
    "JSONEncoder",
    "overload_stdlib",
    "restore_stdlib",
    "reset_modules",
]

backup_dumps = None
backup_dump = None
backup_loads = None
backup_load = None


def import_modules():
    for name in MODULES:
        with contextlib.suppress(Exception):
            yield importlib.import_module(name)
            break


MODULES_IMPORTS = list(import_modules())
MODULES_NAME = [module.__name__ for module in MODULES_IMPORTS]

for item in MODULES:
    with contextlib.suppress(ValueError):
        index = MODULES_NAME.index(item)
        mainjson = MODULES_IMPORTS[index]
        if mainjson:
            json_module = item
            break

if mainjson is None:
    mainjson = stblib_json
    json_module = "json"


def reset_modules():
    global MODULES_IMPORTS, MODULES_NAME, mainjson, json_module
    MODULES_IMPORTS = list(import_modules())
    MODULES_NAME = [module.__name__ for module in MODULES_IMPORTS]
    for item in MODULES:
        with contextlib.suppress(ValueError):
            index = MODULES_NAME.index(item)
            mainjson = MODULES_IMPORTS[index]

            if mainjson:
                json_module = item
                break
    if mainjson is None:
        mainjson = stblib_json
        json_module = "json"


def dumps(obj, **kw):
    output = mainjson.dumps(obj)
    if json_module == "orjson" and hasattr(output, "decode"):
        output = output.decode("utf-8")
    return output


def loads(obj, **kw):
    try:
        output = mainjson.loads(obj)
    except ValueError as e:
        raise stblib_json.JSONDecodeError(str(e), "", 0)
    if json_module == "orjson" and hasattr(output, "decode"):
        output = output.decode("utf-8")
    return output


def dump(obj, fp, **kw):
    return fp.write(dumps(obj, **kw))


def load(fp, **kw):
    data = fp.read()
    return loads(data, **kw)


def overload_stdlib():
    global backup_dumps, backup_dump, backup_loads, backup_load
    import json

    if json_module == "json":
        return

    if not backup_dumps and json.dumps is not dumps:
        backup_dumps = json.dumps
        backup_dump = json.dump
        backup_loads = json.loads
        backup_load = json.load

    json.loads = loads
    json.load = load
    json.dumps = dumps
    json.dump = dump


def restore_stdlib():
    import json

    if json_module == "json":
        return
    if backup_dumps and json.dumps is dumps:
        json.loads = backup_loads
        json.load = backup_load
        json.dumps = backup_dumps
        json.dump = backup_dump
