# -*- coding: utf-8 -*-
import collections
import inspect
import json
import sys


__version__ = "1.4"


SUPPORTED_FUNCS = ["loads", "load", "dumps", "dump"]


json_module = collections.namedtuple("json_module", " ".join(SUPPORTED_FUNCS))


try:
    import ujson  # https://github.com/esnme/ultrajson
except ImportError:
    ujson = False

try:
    import rapidjson  # https://github.com/python-rapidjson/python-rapidjson
except ImportError:
    rapidjson = False

try:
    import simplejson  # https://github.com/simplejson/simplejson

    simplejson_slow = False
    if not simplejson.encoder.c_make_encoder:
        simplejson, simplejson_slow = simplejson_slow, simplejson
except ImportError:
    simplejson = simplejson_slow = False

try:
    import nssjson  # https://github.com/lelit/nssjson

    nssjson_slow = False
    if not nssjson.encoder.c_make_encoder:
        nssjson, nssjson_slow = nssjson_slow, nssjson
except ImportError:
    nssjson = nssjson_slow = False

try:
    import yajl  # https://github.com/rtyler/py-yajl
except ImportError:
    yajl = False

try:
    import cjson  # https://github.com/AGProjects/python-cjson

    cjson = json_module(dump=None, dumps=cjson.encode, load=None, loads=cjson.decode)
except ImportError:
    cjson = None

try:
    import metamagic.json as mjson  # https://github.com/sprymix/metamagic.json
except ImportError:
    mjson = False

try:
    import orjson  # https://github.com/ijl/orjson
except ImportError:
    orjson = False

try:
    pypy = sys.pypy_version_info is not None
except AttributeError:
    pypy = False

try:
    basestring
except NameError:
    basestring = str

if pypy:
    # NOTE(mattgiles): in benchmarks, using pypy, the standard library's json
    # module outperforms all third party libraries.
    DEFAULT_RANKINGS = {"dump": [], "dumps": [], "load": [], "loads": []}

elif sys.version_info.major == 3:
    DEFAULT_RANKINGS = {
        "dump": [rapidjson, ujson, yajl, json, nssjson, simplejson, nssjson_slow, simplejson_slow],
        "dumps": [
            orjson,
            mjson,
            rapidjson,
            ujson,
            yajl,
            json,
            nssjson,
            simplejson,
            nssjson_slow,
            simplejson_slow,
        ],
        "load": [ujson, simplejson, rapidjson, json, nssjson, yajl, nssjson_slow, simplejson_slow],
        "loads": [
            orjson,
            ujson,
            simplejson,
            rapidjson,
            json,
            nssjson,
            yajl,
            nssjson_slow,
            simplejson_slow,
        ],
    }

else:
    DEFAULT_RANKINGS = {
        "dump": [ujson, yajl, json, nssjson, simplejson, nssjson_slow, simplejson_slow],
        "dumps": [ujson, yajl, json, cjson, nssjson, simplejson, nssjson_slow, simplejson_slow],
        "load": [ujson, simplejson, nssjson, yajl, json, simplejson_slow, nssjson_slow],
        "loads": [cjson, ujson, simplejson, nssjson, yajl, json, simplejson_slow, nssjson_slow],
    }


def _get_kwarg_names(func):
    try:
        # NOTE(mattgiles): there are compatibility issues between Python2 and
        # Python3 when using `inspect.getargspec`. Here we elect to try
        # Python27-compliant code first, falling back to Python36. This order
        # is important because of the behavior of intermediate Python versions.
        return inspect.getargspec(func)[0]
    except (AttributeError, TypeError, ValueError):
        return inspect.getfullargspec(func).kwonlyargs


def _best_available_json_func(func_name, ranking, **kwargs):
    _available = []
    for module in ranking:
        if isinstance(module, basestring):
            if module not in globals():
                try:
                    globals()[module] = __import__(module)
                except ModuleNotFoundError:
                    globals()[module] = False
            if globals()[module]:
                _available.append(globals()[module])
        else:
            if module:
                _available.append(module)

    if not kwargs:
        return getattr(_available[0], func_name)

    for module in _available:
        try:
            func = getattr(module, func_name)
            supported = _get_kwarg_names(func)
            if set(kwargs.keys()).issubset(supported):
                return func
        except (AttributeError, TypeError, ValueError):
            continue

    return getattr(json, func_name)


def mujson_function(name, alias_for=None, ranking=None):
    """Return the "best" available version of some JSON function.

    The true performance ranking of different JSON libraries varies widely
    based on the actual JSON data being encoded or decoded. Therefore, it may
    be desirable to pass your own `ranking` based on your knowledge of the
    common shape or characteristics of the JSON data relevant to your project.

    Args:
        name (str): the global name of your mujson function. Must have the same
          string value as the variable to which you assign the output of
          `mujson_function()`. mujson will infer the underlying json function
          from the name if that function is in the name.
        alias_for (str): the json function for which your mujson function is
          an alias. Must be one of ["load", "loads", "dump", "dumps"].
        ranking (list): if a list, will use ranking when evaluating
          the best module available. If not passed, the default rankings will
          be used.

    NOTE(mattgiles): the returned function behaves differently the first time
    it is invoked, compared to subsequent times. On first invocation, before
    any output is returned, the "best" implementation of the desired json
    function that is available for import is retrieved and made to replace the
    temporary function returned by `mujson_function` in the global namespace.
    The reason for this hackery is because, given the implicit desire for
    speed, extra function calls are are needlessly slow.

    """
    if alias_for is None:
        for func in SUPPORTED_FUNCS:
            if name.find(func) >= 0:
                alias_for = func
                break

    if alias_for is None:
        raise ValueError(
            "mujson_function requires that either `name` contains a substring "
            "in {} or that `alias_for` is specified.".format(SUPPORTED_FUNCS)
        )

    if alias_for not in SUPPORTED_FUNCS:
        raise ValueError("`alias_for` must be one of: {}".format(SUPPORTED_FUNCS))

    if ranking is None:
        ranking = DEFAULT_RANKINGS[alias_for]

    def temp_json_func(*args, **kwargs):
        func = _best_available_json_func(alias_for, ranking, **kwargs)
        globals()[name] = func
        if isinstance(r := func(*args, **kwargs), (bytes, bytearray)):
            return r.decode()
        return r

    return temp_json_func


dump = mujson_function("dump")

dumps = mujson_function("dumps")

load = mujson_function("load")

loads = mujson_function("loads")


# NOTE(mattgiles): programmers can elect to explicitly import `compliant_*`
# versions of the standard functions to avoid run time errors that depend on
# what concrete uses of e.g. `mujson.dumps` hit `mujson_function:temp_json_func`
# first. Although `mujson_function` guarantees that the first time it is called
# it protects against choosing a JSON library which does not support invoked
# kwargs, this dynamic behavior can lead to NON-DETERMINISTIC behavior in
# larger or more complex libraries where mujson is used multiple places with
# varying signatures.
NON_COMPLIANT = [ujson, cjson, mjson, orjson]

compliant_dump = mujson_function(
    "compliant_dump", ranking=[m for m in DEFAULT_RANKINGS["dump"] if m not in NON_COMPLIANT]
)

compliant_dumps = mujson_function(
    "compliant_dumps", ranking=[m for m in DEFAULT_RANKINGS["dumps"] if m not in NON_COMPLIANT]
)

compliant_load = mujson_function(
    "compliant_load", ranking=[m for m in DEFAULT_RANKINGS["load"] if m not in NON_COMPLIANT]
)

compliant_loads = mujson_function(
    "compliant_loads", ranking=[m for m in DEFAULT_RANKINGS["loads"] if m not in NON_COMPLIANT]
)
