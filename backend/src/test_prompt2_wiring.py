import asyncio
from livekit.agents import RunContext
import services
from agent import Assistant
import db

class MockRunContext:
    pass

async def test_prompt2_wiring():
    print("--- Testing Prompt 2 Shared Function Wiring ---")
    db.init_db()
    assistant = Assistant()

    # Helper to invoke function_tool method on Assistant class
    def call_tool(method_name: str, *args):
        tool_method = getattr(assistant, method_name, None)
        assert tool_method is not None, f"Tool '{method_name}' not found on Assistant!"
        return tool_method(MockRunContext(), *args)

    # Test 1: lookup_product
    print("\n1. Testing lookup_product('milk'):")
    direct_prod = services.lookup_product("milk")
    tool_prod = call_tool("lookup_product", "milk")
    print(f"Direct Service: {direct_prod}")
    print(f"Agent Tool:     {tool_prod}")
    assert direct_prod == tool_prod, "FAIL: lookup_product results differ!"

    # Test 2: check_order_status
    print("\n2. Testing check_order_status('ord_001'):")
    direct_order = services.check_order_status("ord_001")
    tool_order = call_tool("check_order_status", "ord_001")
    print(f"Direct Service: {direct_order}")
    print(f"Agent Tool:     {tool_order}")
    assert direct_order == tool_order, "FAIL: check_order_status results differ!"

    # Test 3: get_shop_info
    print("\n3. Testing get_shop_info():")
    direct_shop = services.get_shop_info()
    tool_shop = call_tool("get_shop_info")
    print(f"Direct Service: {direct_shop}")
    print(f"Agent Tool:     {tool_shop}")
    assert direct_shop == tool_shop, "FAIL: get_shop_info results differ!"

    print("\nALL PROMPT 2 WIRING TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(test_prompt2_wiring())
