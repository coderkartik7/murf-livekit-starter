import asyncio
from livekit.agents import RunContext
import services
from agent import Assistant
import db

# Dummy RunContext mock
class MockRunContext:
    pass

async def test_end_to_end():
    print("Testing Shared Function wiring end-to-end...")
    # Initialize the DB so tables and seed data are created.
    db.init_db()
    
    # 1. Test direct services call
    shop_id = "primary_shop"
    direct_res = services.get_shop_status(shop_id)
    print(f"Direct Service Result: {direct_res}")
    
    # 2. Test LiveKit Agent @function_tool invocation
    # Create instance of Assistant
    assistant = Assistant()
    # Find the tool method
    tool_method = None
    for name, attr in type(assistant).__dict__.items():
        if name == "get_shop_status":
            tool_method = attr
            break
            
    if not tool_method:
        print("FAIL: get_shop_status tool not found on Assistant!")
        return
        
    # Invoke tool method
    # Since it is defined as sync 'def get_shop_status', call it directly
    tool_res = tool_method(assistant, MockRunContext(), shop_id)
    print(f"Tool Call Result: {tool_res}")
    
    # Verify results match
    assert direct_res == tool_res, "FAIL: Tool result and service result do not match!"
    print("SUCCESS: Tool and service results match!")

if __name__ == "__main__":
    asyncio.run(test_end_to_end())
