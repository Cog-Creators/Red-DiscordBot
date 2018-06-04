import pytest
from redbot.core.rpc import RPC, get_name


@pytest.fixture()
def rpc(red):
    return RPC(red)


@pytest.fixture()
def cog():
    class Cog:
        async def cofunc(*args, **kwargs):
            pass

        async def cofunc2(*args, **kwargs):
            pass

        async def cofunc3(*args, **kwargs):
            pass

        def func(*args, **kwargs):
            pass
    return Cog()


@pytest.fixture()
def existing_func(rpc, cog):
    rpc.add_method(cog.cofunc)

    return cog.cofunc


@pytest.fixture()
def existing_multi_func(rpc, cog):
    funcs = [cog.cofunc, cog.cofunc2, cog.cofunc3]
    rpc.add_multi_method(*funcs)

    return funcs


def test_get_name(cog):
    assert get_name(cog.cofunc) == "cog__cofunc"
    assert get_name(cog.cofunc2) == "cog__cofunc2"
    assert get_name(cog.func) == "cog__func"


def test_add_method(rpc, cog):
    rpc.add_method(cog.cofunc)

    assert get_name(cog.cofunc) in rpc._rpc.methods


def test_double_add(rpc, cog):
    rpc.add_method(cog.cofunc)
    count = len(rpc._rpc.methods)

    rpc.add_method(cog.cofunc)

    assert count == len(rpc._rpc.methods)


def test_add_notcoro_method(rpc, cog):
    with pytest.raises(TypeError):
        rpc.add_method(cog.func)


def test_add_multi(rpc, cog):
    funcs = [cog.cofunc, cog.cofunc2, cog.cofunc3]
    rpc.add_multi_method(*funcs)

    names = [get_name(f) for f in funcs]

    assert all(n in rpc._rpc.methods for n in names)


def test_add_multi_bad(rpc, cog):
    funcs = [cog.cofunc, cog.cofunc2, cog.cofunc3, cog.func]

    with pytest.raises(TypeError):
        rpc.add_multi_method(*funcs)

    names = [get_name(f) for f in funcs]

    assert not any(n in rpc._rpc.methods for n in names)


def test_remove_method(rpc, existing_func):
    before_count = len(rpc._rpc.methods)
    rpc.remove_method(existing_func)

    assert get_name(existing_func) not in rpc._rpc.methods
    assert before_count - 1 == len(rpc._rpc.methods)


def test_remove_multi_method(rpc, existing_multi_func):
    before_count = len(rpc._rpc.methods)
    name = get_name(existing_multi_func[0])
    prefix = name.split("__")[0]

    rpc.remove_methods(prefix)

    assert before_count - len(existing_multi_func) == len(rpc._rpc.methods)

    names = [get_name(f) for f in existing_multi_func]

    assert not any(n in rpc._rpc.methods for n in names)
