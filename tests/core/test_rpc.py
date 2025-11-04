import pytest
import tempfile
import textwrap
import asyncio
import json
import aiohttp
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
            self.temp_dir = Path(str(tmpdir))
            self.module_path = self.temp_dir / f"{cog_name}.py"
            
            # Generate handler methods
            handler_methods = []
            for handler_name, return_value in handlers.items():
                handler_methods.append(f"""
    async def {handler_name}(self):
        return "{return_value}"
""")
            
            # Generate RPC handler registration calls
            rpc_registrations = []
            for handler_name in handlers.keys():
                rpc_registrations.append(f"        self.bot.register_rpc_handler(self.{handler_name})")
            
            # Generate cog class code
            cog_code = textwrap.dedent(f"""
from redbot.core import commands

class {cog_name.title()}(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
{chr(10).join(rpc_registrations)}
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
    await red._cog_mgr.add_path(Path(str(tmpdir)))
    
    try:
        # Load the cog via RPC
        await core_logic._load([cog_name])
        
        # Verify cog is loaded
        assert cog_name in red.extensions
        
        # Call RPC handler and verify initial behavior
        handler_name = f"{cog_name.upper()}__TEST_HANDLER"
        assert handler_name in red.rpc._rpc.methods
        
        # Capture the original handler reference before reload
        original_handler = red.rpc._rpc.methods[handler_name].method
        result = await original_handler()
        assert result == "version_1"
        
        # Modify the module file to return different value
        test_cog_module.update_handlers({"test_handler": "version_2"})
        
        # Reload the cog via RPC
        await core_logic._reload([cog_name])
        
        # Verify cog is still loaded
        assert cog_name in red.extensions
        
        # Capture the new handler reference after reload
        new_handler = red.rpc._rpc.methods[handler_name].method
        
        # Verify the handler reference itself updated (not just the return value)
        assert original_handler is not new_handler, "Handler reference should update after reload"
        assert id(original_handler) != id(new_handler), "Handler object identity should differ after reload"
        
        # Call RPC handler and verify it now executes new code
        result = await new_handler()
        assert result == "version_2", "RPC handler should execute new code after reload"
        
    finally:
        # Clean up
        if cog_name in red.extensions:
            await core_logic._unload([cog_name])
        await red._cog_mgr.remove_path(Path(str(tmpdir)).resolve())


@pytest.mark.asyncio
async def test_rpc_reload_flow_matches_unload_load(red, core_logic, test_cog_module, tmpdir):
    """Test that _reload() matches _unload() + _load() behavior."""
    # Create test cog module
    cog_name = "flowtest"
    handlers = {"flow_handler": "initial"}
    test_cog_module.create_module(cog_name, handlers, tmpdir)
    
    # Add temp directory to cog paths
    await red._cog_mgr.add_path(Path(str(tmpdir)))
    
    try:
        # Load the cog and verify initial behavior
        await core_logic._load([cog_name])
        handler_name = f"{cog_name.upper()}__FLOW_HANDLER"
        
        # Capture original handler reference
        original_handler = red.rpc._rpc.methods[handler_name].method
        result = await original_handler()
        assert result == "initial"
        
        # Modify the module file
        test_cog_module.update_handlers({"flow_handler": "after_reload"})
        
        # Test _reload() behavior
        await core_logic._reload([cog_name])
        
        # Capture new handler reference and verify it updated
        new_handler = red.rpc._rpc.methods[handler_name].method
        assert original_handler is not new_handler, "Handler reference should update after _reload"
        
        result = await new_handler()
        assert result == "after_reload"
        
        # Unload the cog
        await core_logic._unload([cog_name])
        assert cog_name not in red.extensions
        assert handler_name not in red.rpc._rpc.methods
        
        # Modify the module file again
        test_cog_module.update_handlers({"flow_handler": "after_manual_load"})
        
        # Load again and verify it loads the latest version
        await core_logic._load([cog_name])
        
        # Capture final handler reference and verify it's different from reload handler
        final_handler = red.rpc._rpc.methods[handler_name].method
        assert new_handler is not final_handler, "Handler reference should update after manual load"
        
        result = await final_handler()
        assert result == "after_manual_load"
        
    finally:
        # Clean up
        if cog_name in red.extensions:
            await core_logic._unload([cog_name])
        await red._cog_mgr.remove_path(Path(str(tmpdir)).resolve())


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
    await red._cog_mgr.add_path(Path(str(tmpdir)))
    
    try:
        # Load the cog
        await core_logic._load([cog_name])
        
        # Verify all handlers work with initial values
        handler_names = [f"{cog_name.upper()}__HANDLER_ONE",
                        f"{cog_name.upper()}__HANDLER_TWO",
                        f"{cog_name.upper()}__HANDLER_THREE"]
        
        for handler_name in handler_names:
            assert handler_name in red.rpc._rpc.methods
            
        # Capture original handler references before reload
        original_handlers = [red.rpc._rpc.methods[name].method for name in handler_names]
        
        result_one = await original_handlers[0]()
        result_two = await original_handlers[1]()
        result_three = await original_handlers[2]()
        
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
        
        # Capture new handler references after reload
        new_handlers = [red.rpc._rpc.methods[name].method for name in handler_names]
        
        # Verify all handler references updated (not just return values)
        for i, (original, new) in enumerate(zip(original_handlers, new_handlers)):
            assert original is not new, f"Handler {i+1} reference should update after reload"
            assert id(original) != id(new), f"Handler {i+1} object identity should differ after reload"
        
        # Verify all handlers now execute new code
        result_one = await new_handlers[0]()
        result_two = await new_handlers[1]()
        result_three = await new_handlers[2]()
        
        assert result_one == "one_v2", "First handler should execute new code"
        assert result_two == "two_v2", "Second handler should execute new code"
        assert result_three == "three_v2", "Third handler should execute new code"
        
    finally:
        # Clean up
        if cog_name in red.extensions:
            await core_logic._unload([cog_name])
        await red._cog_mgr.remove_path(Path(str(tmpdir)).resolve())


@pytest.mark.asyncio
async def test_rpc_reload_flow_via_rpc_interface(red, core_logic, test_cog_module, tmpdir):
    """Test RPC reload using the actual rpc_reload() method instead of _reload()."""
    # Create test cog module
    cog_name = "rpctest"
    handlers = {"rpc_handler": "rpc_v1"}
    test_cog_module.create_module(cog_name, handlers, tmpdir)
    
    # Add temp directory to cog paths
    await red._cog_mgr.add_path(Path(str(tmpdir)))
    
    try:
        # Load the cog initially
        await core_logic._load([cog_name])
        
        # Verify cog is loaded and handler works
        assert cog_name in red.extensions
        handler_name = f"{cog_name.upper()}__RPC_HANDLER"
        assert handler_name in red.rpc._rpc.methods
        
        # Capture original handler reference before reload
        original_handler = red.rpc._rpc.methods[handler_name].method
        result = await original_handler()
        assert result == "rpc_v1"
        
        # Modify the module file to return different value
        test_cog_module.update_handlers({"rpc_handler": "rpc_v2"})
        
        # Create a minimal request-like object with params
        class MockRequest:
            def __init__(self, params):
                self.params = params
        
        request = MockRequest([cog_name])
        
        # Reload using the actual rpc_reload method
        await core_logic.rpc_reload(request)
        
        # Verify cog is still loaded
        assert cog_name in red.extensions
        
        # Verify RPC handler name remains present
        assert handler_name in red.rpc._rpc.methods
        
        # Capture new handler reference after rpc_reload
        new_handler = red.rpc._rpc.methods[handler_name].method
        
        # Verify the handler reference itself updated via rpc_reload
        assert original_handler is not new_handler, "Handler reference should update after rpc_reload"
        assert id(original_handler) != id(new_handler), "Handler object identity should differ after rpc_reload"
        
        # Verify invoking the handler now returns updated value
        result = await new_handler()
        assert result == "rpc_v2", "RPC handler should execute new code after rpc_reload"
        
    finally:
        # Clean up
        if cog_name in red.extensions:
            await core_logic._unload([cog_name])
        await red._cog_mgr.remove_path(Path(str(tmpdir)).resolve())


@pytest.mark.asyncio
@pytest.mark.skip_ci  # Skip in CI if network tests are restricted
async def test_rpc_reload_via_http_endpoint_smoke_test(red, core_logic, test_cog_module, tmpdir):
    """Smoke test that validates RPC reload through actual HTTP endpoint to mirror real usage."""
    import os
    
    # Skip test if running in CI environment or if explicitly disabled
    if os.environ.get("CI") or os.environ.get("SKIP_NETWORK_TESTS"):
        pytest.skip("Skipping network test in CI or when SKIP_NETWORK_TESTS is set")
    
    # Create test cog module
    cog_name = "httptest"
    handlers = {"http_handler": "http_v1"}
    test_cog_module.create_module(cog_name, handlers, tmpdir)
    
    # Add temp directory to cog paths
    await red._cog_mgr.add_path(Path(str(tmpdir)))
    
    # Initialize RPC system
    await red.rpc._pre_login()
    
    # Start RPC server on ephemeral port (0 = random available port)
    from aiohttp import web
    app = web.Application()
    app.router.add_post('/jsonrpc', red.rpc._rpc)
    
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Use ephemeral port for testing
    site = web.TCPSite(runner, 'localhost', 0)
    await site.start()
    
    # Get the actual port assigned
    server_port = site._server.sockets[0].getsockname()[1]
    server_url = f"http://localhost:{server_port}/jsonrpc"
    
    try:
        # Load the cog initially
        await core_logic._load([cog_name])
        
        # Verify cog is loaded
        assert cog_name in red.extensions
        handler_name = f"{cog_name.upper()}__HTTP_HANDLER"
        assert handler_name in red.rpc._rpc.methods
        
        async with aiohttp.ClientSession() as session:
            # Test 1: Call the handler via HTTP RPC to verify initial behavior
            payload = {
                "jsonrpc": "2.0",
                "method": handler_name,
                "params": [],
                "id": 1
            }
            
            async with session.post(server_url, json=payload) as resp:
                assert resp.status == 200
                result = await resp.json()
                assert result["result"] == "http_v1"
                assert "error" not in result
            
            # Modify the module file to return different value
            test_cog_module.update_handlers({"http_handler": "http_v2"})
            
            # Test 2: Call rpc_reload via HTTP RPC
            reload_payload = {
                "jsonrpc": "2.0", 
                "method": "CORE__RPC_RELOAD",
                "params": [cog_name],
                "id": 2
            }
            
            async with session.post(server_url, json=reload_payload) as resp:
                assert resp.status == 200
                result = await resp.json()
                assert "error" not in result, f"RPC reload failed: {result.get('error', 'Unknown error')}"
            
            # Verify cog is still loaded after reload
            assert cog_name in red.extensions
            assert handler_name in red.rpc._rpc.methods
            
            # Test 3: Call the handler again via HTTP RPC to verify new behavior
            updated_payload = {
                "jsonrpc": "2.0",
                "method": handler_name,
                "params": [],
                "id": 3
            }
            
            async with session.post(server_url, json=updated_payload) as resp:
                assert resp.status == 200
                result = await resp.json()
                assert result["result"] == "http_v2", "Handler should execute new code after HTTP RPC reload"
                assert "error" not in result
            
            # Test 4: Verify we can call the handler multiple times with consistent results
            for i in range(3):
                consistency_payload = {
                    "jsonrpc": "2.0",
                    "method": handler_name,
                    "params": [],
                    "id": 10 + i
                }
                
                async with session.post(server_url, json=consistency_payload) as resp:
                    assert resp.status == 200
                    result = await resp.json()
                    assert result["result"] == "http_v2", f"Handler should be consistent on call {i+1}"
            
            # Test 5: Verify error handling for non-existent methods
            error_payload = {
                "jsonrpc": "2.0",
                "method": "NONEXISTENT__METHOD",
                "params": [],
                "id": 4
            }
            
            async with session.post(server_url, json=error_payload) as resp:
                assert resp.status == 200
                result = await resp.json()
                assert "error" in result, "Should return error for non-existent method"
    
    finally:
        # Clean up server
        await runner.cleanup()
        
        # Clean up cog and paths
        if cog_name in red.extensions:
            await core_logic._unload([cog_name])
        await red._cog_mgr.remove_path(Path(str(tmpdir)).resolve())
