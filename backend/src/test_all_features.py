import sys
from pathlib import Path

# Add backend/src to path
src_dir = Path(__file__).resolve().parent
sys.path.insert(0, str(src_dir))

import db
import services
from agent import Assistant

def run_tests():
    sys.stdout.reconfigure(encoding='utf-8')
    print("=== Testing DukaanMitra Feature Implementation ===")
    db.init_db()

    # 1. Sales Ledger & Role Restriction
    print("\n1. Testing log_sale & role restriction:")
    res_owner = services.log_sale("Basmati Rice", 5.0, "kg", 350.0, user_role="owner")
    assert res_owner["status"] == "success", f"Owner log_sale failed: {res_owner}"
    print("  [SUCCESS] Owner log_sale:", res_owner["message"])

    res_cust = services.log_sale("Basmati Rice", 5.0, "kg", 350.0, user_role="customer")
    assert res_cust["status"] == "error" and "Access denied" in res_cust["message"], f"Role restriction failed: {res_cust}"
    print("  [SUCCESS] Customer log_sale correctly rejected with access denied.")

    # 2. Credit Tracker & Role Restriction & Balance calculation
    print("\n2. Testing log_credit & check_credit_balance:")
    res_cred1 = services.log_credit("Ramesh Kumar", 500.0, "given", "Groceries", user_role="owner")
    assert res_cred1["status"] == "success", f"Owner log_credit failed: {res_cred1}"
    res_cred2 = services.log_credit("Ramesh Kumar", 200.0, "paid", "UPI Payment", user_role="owner")
    assert res_cred2["status"] == "success", f"Owner log_credit paid failed: {res_cred2}"

    res_cred_cust = services.log_credit("Ramesh Kumar", 500.0, "given", user_role="customer")
    assert res_cred_cust["status"] == "error", "Customer log_credit should be rejected"
    print("  [SUCCESS] Customer log_credit correctly rejected.")

    bal_res = services.check_credit_balance("Ramesh Kumar")
    assert bal_res["status"] == "success", f"check_credit_balance failed: {bal_res}"
    assert bal_res["balance"] == 300.0, f"Balance mismatch! Expected 300.0, got {bal_res['balance']}"
    print(f"  [SUCCESS] Credit balance calculation verified for Ramesh Kumar: ₹{bal_res['balance']} (Given ₹500 - Paid ₹200).")

    # 3. Messages for Owner
    print("\n3. Testing leave_message_for_owner & get_messages:")
    msg_res = services.leave_message_for_owner("Sita Devi", "Please keep 1 packet milk aside", "user_sita")
    assert msg_res["status"] == "success", f"leave_message failed: {msg_res}"
    print("  [SUCCESS] Message saved:", msg_res["message"])

    all_msgs = services.get_messages()
    assert all_msgs["status"] == "success" and len(all_msgs["messages"]) > 0
    print("  [SUCCESS] Retrieved messages list count:", len(all_msgs["messages"]))

    # 4. Customer History (Merged Call Logs + Messages)
    print("\n4. Testing get_customer_history:")
    call_res = services.log_call_summary("Rahul Sharma", "customer", "Inquired about milk availability and store timing.")
    assert call_res["status"] == "success", f"log_call_summary failed: {call_res}"
    
    cust_hist = services.get_customer_history(user_role="owner")
    assert cust_hist["status"] == "success", f"get_customer_history failed: {cust_hist}"
    history_items = cust_hist["history"]
    assert len(history_items) >= 2, "Expected at least 2 items in merged history"
    types_found = {item["type"] for item in history_items}
    assert "call" in types_found and "message" in types_found, f"Expected both call and message types, got: {types_found}"
    print(f"  [SUCCESS] Merged customer history contains {len(history_items)} items with types: {types_found}.")

    cust_hist_denied = services.get_customer_history(user_role="customer")
    assert cust_hist_denied["status"] == "error", "Customer get_customer_history should be denied"
    print("  [SUCCESS] Customer get_customer_history correctly denied.")


    # 5. Daily Summary
    print("\n5. Testing get_daily_summary:")
    summary = services.get_daily_summary()
    assert summary["status"] == "success"
    print(f"  [SUCCESS] Daily Summary aggregate: Total ₹{summary['total_amount']}, Transactions: {summary['transaction_count']}, Best Item: {summary['best_selling_item']}")

    # 6. Shop Hours (UI only)
    print("\n6. Testing update_shop_hours:")
    hours_res = services.update_shop_hours("8:00 AM - 10:00 PM", "Shop #12, Chandni Chowk, Delhi")
    assert hours_res["status"] == "success"
    print("  [SUCCESS] Shop hours updated:", hours_res["hours"])

    # 7. Market Watch (Agmarknet Live API)
    print("\n7. Testing get_market_price (Agmarknet API):")
    mkt_res = services.get_market_price("Rice", state="Delhi")
    print("  [RESULT] Market Watch status:", mkt_res["status"], "| Response:", mkt_res.get("price") or mkt_res.get("message"))

    print("\n=== ALL FEATURE IMPLEMENTATION TESTS PASSED PERFECTLY! ===")

if __name__ == "__main__":
    run_tests()
