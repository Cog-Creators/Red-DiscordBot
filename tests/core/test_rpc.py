import pytest
import tempfile
import textwrap
from pathlib import Path

from redbot.pytest.rpc import *
from redbot.core._rpc import get_name


def test_get_name(cog):
    assert get_name(cog.cofunc) == "COG__COFUNC"
    assert get_name(cog.cofunc2) == "COG__COFUNC2"
    assert get_name(cog.func) == "COG__FUNC"


def test_internal_methods_exist(rpc):
    assert "GET_METHODS" in rpc._rpc.methods


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


def test_rpcmixin_register(rpcmixin, cog):
    rpcmixin.register_rpc_handler(cog.cofunc)

    assert rpcmixin.rpc.add_method.called_once_with(cog.cofunc)

    name = get_name(cog.cofunc)
    cogname = name.split("__")[0]

    assert cogname in rpcmixin.rpc_handlers


def test_rpcmixin_unregister(rpcmixin, cog):
    rpcmixin.register_rpc_handler(cog.cofunc)
    rpcmixin.unregister_rpc_handler(cog.cofunc)

    assert rpcmixin.rpc.remove_method.called_once_with(cog.cofunc)

    name = get_name(cog.cofunc)
    cogname = name.split("__")[0]

    if cogname in rpcmixin.rpc_handlers:
        assert cog.cofunc not in rpcmixin.rpc_handlers[cogname]


@pytest.fixture()
def test_cog_module():
    """Helper fixture to generate temporary test cog modules."""
    class TestCogHelper:
        def __init__(self):
            self.temp_dir = None
            self.module_path = None
            
        def create_module(self, cog_name, handlers, tmpdir):
            """Create a temporary cog module with specified handlers."""
            self.temp_dir = Path(tmpdir)
            self.module_path = self.temp_dir / f"{cog_name}.py"
            
            # Generate handler methods
            handler_methods = []
            for handler_name, return_value in handlers.items():
                handler_methods.append(f"""
    async def {handler_name}(self):
        return "{return_value}"
""")
            
            # Generate cog class code
            cog_code = textwrap.dedent(f"""
from redbot.core import commands

class {cog_name.title()}(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
{''.join(handler_methods)}

def setup(bot):
    bot.add_cog({cog_name.title()}(bot))
""").strip()
            
            self.module_path.write_text(cog_code, encoding="utf-8")
            return self.module_path
            
        def update_handlers(self, handlers):
            """Update handler return values in the module file."""
            if not self.module_path or not self.module_path.exists():
                raise RuntimeError("Module not created yet")
                
            content = self.module_path.read_text(encoding="utf-8")
            
            # Update each handler's return value
            for handler_name, new_return_value in handlers.items():
                # Find and replace the return statement for this handler
                import re
                pattern = rf'(async def {handler_name}\(self\):\s*return )"[^"]*"'
                replacement = rf'\1"{new_return_value}"'
                content = re.sub(pattern, replacement, content)
                
            self.module_path.write_text(content, encoding="utf-8")
            
    return TestCogHelper()


@pytest.mark.asyncio
async def test_rpc_handler_updates_on_reload(red, core_logic, test_cog_module, tmpdir):
    """Test that RPC handlers execute new code after reload."""
    # Create test cog module
    cog_name = "testcog"
    handlers = {"test_handler": "version_1"}
    test_cog_module.create_module(cog_name, handlers, tmpdir)
    
    # Add temp directory to cog paths
    await red._cog_mgr.add_path(Path(tmpdir))
    
    try:
        # Load the cog via RPC
        await core_logic._load([cog_name])
        
        # Verify cog is loaded
        assert f"{cog_name}.{cog_name}" in red.extensions
        
        # Call RPC handler and verify initial behavior
        handler_name = f"{cog_name.upper()}__TEST_HANDLER"
        assert handler_name in red.rpc._rpc.methods
        result = await red.rpc._rpc.methods[handler_name]()
        assert result == "version_1"
        
        # Modify the module file to return different value
        test_cog_module.update_handlers({"test_handler": "version_2"})
        
        # Reload the cog via RPC
        await core_logic._reload([cog_name])
        
        # Verify cog is still loaded
        assert f"{cog_name}.{cog_name}" in red.extensions
        
        # Call RPC handler and verify it now executes new code
        result = await red.rpc._rpc.methods[handler_name]()
        assert result == "version_2", "RPC handler should execute new code after reload"
        
    finally:
        # Clean up
        if f"{cog_name}.{cog_name}" in red.extensions:
            await core_logic._unload([cog_name])
        await red._cog_mgr.remove_path(Path(tmpdir))


@pytest.mark.asyncio
async def test_rpc_reload_flow_matches_unload_load(red, core_logic, test_cog_module, tmpdir):
    """Test that _reload() matches _unload() + _load() behavior."""
    # Create test cog module
    cog_name = "flowtest"
    handlers = {"flow_handler": "initial"}
    test_cog_module.create_module(cog_name, handlers, tmpdir)
    
    # Add temp directory to cog paths
    await red._cog_mgr.add_path(Path(tmpdir))
    
    try:
        # Load the cog and verify initial behavior
        await core_logic._load([cog_name])
        handler_name = f"{cog_name.upper()}__FLOW_HANDLER"
        result = await red.rpc._rpc.methods[handler_name]()
        assert result == "initial"
        
        # Modify the module file
        test_cog_module.update_handlers({"flow_handler": "after_reload"})
        
        # Test _reload() behavior
        await core_logic._reload([cog_name])
        result = await red.rpc._rpc.methods[handler_name]()
        assert result == "after_reload"
        
        # Unload the cog
        await core_logic._unload([cog_name])
        assert f"{cog_name}.{cog_name}" not in red.extensions
        assert handler_name not in red.rpc._rpc.methods
        
        # Modify the module file again
        test_cog_module.update_handlers({"flow_handler": "after_manual_load"})
        
        # Load again and verify it loads the latest version
        await core_logic._load([cog_name])
        result = await red.rpc._rpc.methods[handler_name]()
        assert result == "after_manual_load"
        
    finally:
        # Clean up
        if f"{cog_name}.{cog_name}" in red.extensions:
            await core_logic._unload([cog_name])
        await red._cog_mgr.remove_path(Path(tmpdir))


@pytest.mark.asyncio
async def test_multiple_rpc_handlers_update_on_reload(red, core_logic, test_cog_module, tmpdir):
    """Test that multiple RPC handlers all update on reload."""
    # Create test cog module with multiple handlers
    cog_name = "multitest"
    handlers = {
        "handler_one": "one_v1",
        "handler_two": "two_v1",
        "handler_three": "three_v1"
    }
    test_cog_module.create_module(cog_name, handlers, tmpdir)
    
    # Add temp directory to cog paths
    await red._cog_mgr.add_path(Path(tmpdir))
    
    try:
        # Load the cog
        await core_logic._load([cog_name])
        
        # Verify all handlers work with initial values
        handler_names = [f"{cog_name.upper()}__HANDLER_ONE",
                        f"{cog_name.upper()}__HANDLER_TWO",
                        f"{cog_name.upper()}__HANDLER_THREE"]
        
        for handler_name in handler_names:
            assert handler_name in red.rpc._rpc.methods
            
        result_one = await red.rpc._rpc.methods[handler_names[0]]()
        result_two = await red.rpc._rpc.methods[handler_names[1]]()
        result_three = await red.rpc._rpc.methods[handler_names[2]]()
        
        assert result_one == "one_v1"
        assert result_two == "two_v1"
        assert result_three == "three_v1"
        
        # Modify all handlers in the module file
        new_handlers = {
            "handler_one": "one_v2",
            "handler_two": "two_v2",
            "handler_three": "three_v2"
        }
        test_cog_module.update_handlers(new_handlers)
        
        # Reload the cog
        await core_logic._reload([cog_name])
        
        # Verify all handlers now execute new code
        result_one = await red.rpc._rpc.methods[handler_names[0]]()
        result_two = await red.rpc._rpc.methods[handler_names[1]]()
        result_three = await red.rpc._rpc.methods[handler_names[2]]()
        
        assert result_one == "one_v2", "First handler should execute new code"
        assert result_two == "two_v2", "Second handler should execute new code"
        assert result_three == "three_v2", "Third handler should execute new code"
        
    finally:
        # Clean up
        if f"{cog_name}.{cog_name}" in red.extensions:
            await core_logic._unload([cog_name])
        red._cog_mgr.remove_path(Path(tmpdir))
