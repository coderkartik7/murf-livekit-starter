import json
import logging
import os
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

logger = logging.getLogger("agent.services")

# Default DB path: backend/dukaan_mitra.db (sibling of src/)
_DB_PATH = Path(__file__).resolve().parent.parent / "dukaan_mitra.db"


def get_shop_status(shop_id: str = "primary_shop") -> dict:
    """Retrieve details and status for a shop from the database.

    This function represents the single, shared source of truth logic for shop status,
    used both by the LiveKit voice agent tool and the REST endpoint.
    """
    logger.info("Service: Fetching status for shop_id=%s", shop_id)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM shop_info WHERE shop_id = ?", (shop_id,))
        row = cursor.fetchone()
        if row is None:
            return {"status": "error", "message": f"Shop with ID '{shop_id}' not found."}

        record = dict(row)
        return {
            "status": "success",
            "shop_id": record["shop_id"],
            "hours": record["hours_text"],
            "address": record["address_text"],
            "updated_at": record["updated_at"],
        }
    except Exception as e:
        logger.exception("Failed to query shop_info")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def get_shop_info() -> dict:
    """Alias/helper function to fetch primary shop details."""
    return get_shop_status("primary_shop")


def lookup_product(product_name: str) -> dict:
    """Search products table with case-insensitive partial matching.

    Returns price, unit, stock quantity, or "not_found".
    """
    logger.info("Service: Searching product '%s'", product_name)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT * FROM products WHERE name LIKE ? ORDER BY name ASC",
            (f"%{product_name.strip()}%",),
        )
        rows = cursor.fetchall()
        if not rows:
            return {"status": "not_found", "message": f"No product found matching '{product_name}'."}

        matches = []
        for r in rows:
            rec = dict(r)
            matches.append({
                "product_id": rec["product_id"],
                "name": rec["name"],
                "price": rec["price"],
                "unit": rec["unit"],
                "stock_qty": rec["stock_qty"],
                "last_updated": rec["last_updated"],
            })

        return {
            "status": "success",
            "query": product_name,
            "count": len(matches),
            "products": matches,
            "primary_match": matches[0],
        }
    except Exception as e:
        logger.exception("Failed to lookup product")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def check_order_status(query: str) -> dict:
    """Look up order(s) by order_id or customer_user_id.

    Returns order status, delivery slot, items, and total.
    """
    logger.info("Service: Checking order status for query '%s'", query)
    query_str = query.strip()
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM orders 
            WHERE order_id = ? OR customer_user_id = ? 
            ORDER BY created_at DESC
            """,
            (query_str, query_str),
        )
        rows = cursor.fetchall()
        if not rows:
            return {"status": "not_found", "message": f"No order found for '{query}'."}

        orders_list = []
        for r in rows:
            rec = dict(r)
            try:
                items = json.loads(rec["items_json"])
            except Exception:
                items = rec["items_json"]

            orders_list.append({
                "order_id": rec["order_id"],
                "customer_user_id": rec["customer_user_id"],
                "status": rec["status"],
                "delivery_slot": rec["delivery_slot"],
                "total": rec["total"],
                "items": items,
                "created_at": rec["created_at"],
            })

        return {
            "status": "success",
            "query": query_str,
            "latest_order": orders_list[0],
            "all_orders": orders_list,
        }
    except Exception as e:
        logger.exception("Failed to check order status")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def log_sale(item_name: str, quantity: float, unit: str, amount: float, user_role: str = "owner") -> dict:
    """Log a sale transaction into the sales database table.
    
    Enforces role restriction: requires user_role == 'owner'.
    """
    logger.info("Service: log_sale called by role='%s' for item='%s'", user_role, item_name)
    if user_role != "owner":
        return {
            "status": "error",
            "message": "Access denied: Only the shop owner can log sales."
        }

    conn = sqlite3.connect(str(_DB_PATH))
    try:
        cursor = conn.cursor()
        sale_id = f"sale_{uuid.uuid4().hex[:8]}"
        sale_date = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO sales (sale_id, item_name, quantity, unit, amount, sale_date)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (sale_id, item_name.strip(), float(quantity), unit.strip(), float(amount), sale_date),
        )
        conn.commit()
        return {
            "status": "success",
            "sale_id": sale_id,
            "item_name": item_name.strip(),
            "quantity": float(quantity),
            "unit": unit.strip(),
            "amount": float(amount),
            "sale_date": sale_date,
            "message": f"Successfully logged sale of {quantity} {unit} {item_name} for ₹{amount}."
        }
    except Exception as e:
        logger.exception("Failed to log sale")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def log_credit(customer_name: str, amount: float, credit_type: str, note: str = "", user_role: str = "owner") -> dict:
    """Log a credit transaction ('given' or 'paid') for a customer.
    
    Enforces role restriction: requires user_role == 'owner'.
    credit_type must be 'given' or 'paid'.
    """
    logger.info("Service: log_credit called by role='%s' for customer='%s'", user_role, customer_name)
    if user_role != "owner":
        return {
            "status": "error",
            "message": "Access denied: Only the shop owner can log credit transactions."
        }

    norm_type = credit_type.strip().lower()
    if norm_type not in ("given", "paid"):
        return {
            "status": "error",
            "message": f"Invalid credit type '{credit_type}'. Must be 'given' or 'paid'."
        }

    conn = sqlite3.connect(str(_DB_PATH))
    try:
        cursor = conn.cursor()
        credit_id = f"cred_{uuid.uuid4().hex[:8]}"
        created_at = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO credit (credit_id, customer_name, amount, type, note, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (credit_id, customer_name.strip(), float(amount), norm_type, note.strip(), created_at),
        )
        conn.commit()
        return {
            "status": "success",
            "credit_id": credit_id,
            "customer_name": customer_name.strip(),
            "amount": float(amount),
            "type": norm_type,
            "note": note.strip(),
            "created_at": created_at,
            "message": f"Successfully logged credit {norm_type} of ₹{amount} for {customer_name}."
        }
    except Exception as e:
        logger.exception("Failed to log credit")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def check_credit_balance(customer_name: str) -> dict:
    """Calculate and return the net credit balance for a customer.
    
    Balance = sum(given) - sum(paid).
    Returns total given, total paid, net balance, and transaction history.
    """
    logger.info("Service: check_credit_balance for customer='%s'", customer_name)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT * FROM credit 
            WHERE LOWER(customer_name) = LOWER(?)
            ORDER BY created_at DESC
            """,
            (customer_name.strip(),),
        )
        rows = cursor.fetchall()
        total_given = 0.0
        total_paid = 0.0
        history = []
        for r in rows:
            rec = dict(r)
            amt = float(rec["amount"])
            if rec["type"].lower() == "given":
                total_given += amt
            elif rec["type"].lower() == "paid":
                total_paid += amt
            history.append(rec)

        balance = total_given - total_paid
        return {
            "status": "success",
            "customer_name": customer_name.strip(),
            "balance": balance,
            "total_given": total_given,
            "total_paid": total_paid,
            "history": history,
        }
    except Exception as e:
        logger.exception("Failed to check credit balance")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def get_all_credit_balances() -> dict:
    """Get all customer balances for the Credit Tracker UI card."""
    logger.info("Service: get_all_credit_balances called")
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT customer_name, amount, type FROM credit ORDER BY created_at ASC")
        rows = cursor.fetchall()
        customers = {}
        for r in rows:
            rec = dict(r)
            c_name = rec["customer_name"]
            amt = float(rec["amount"])
            if c_name not in customers:
                customers[c_name] = {"given": 0.0, "paid": 0.0}
            if rec["type"].lower() == "given":
                customers[c_name]["given"] += amt
            elif rec["type"].lower() == "paid":
                customers[c_name]["paid"] += amt

        summary_list = []
        for name, data in customers.items():
            bal = data["given"] - data["paid"]
            summary_list.append({
                "customer_name": name,
                "total_given": data["given"],
                "total_paid": data["paid"],
                "balance": bal,
            })

        return {
            "status": "success",
            "customers": summary_list,
        }
    except Exception as e:
        logger.exception("Failed to get all credit balances")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def leave_message_for_owner(from_name: str = "Unknown", message_text: str = "", from_user_id: str = "customer_anon") -> dict:
    """Insert a message from a customer into the messages table."""
    logger.info("Service: leave_message_for_owner from '%s'", from_name)
    name = from_name.strip() if from_name and from_name.strip() else "Unknown"
    text = message_text.strip() if message_text else ""
    if not text:
        return {"status": "error", "message": "Message text cannot be empty."}

    conn = sqlite3.connect(str(_DB_PATH))
    try:
        cursor = conn.cursor()
        msg_id = f"msg_{uuid.uuid4().hex[:8]}"
        created_at = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO messages (message_id, from_user_id, from_name, message_text, created_at, read_flag)
            VALUES (?, ?, ?, ?, ?, 0)
            """,
            (msg_id, from_user_id, name, text, created_at),
        )
        conn.commit()
        return {
            "status": "success",
            "message_id": msg_id,
            "from_name": name,
            "message_text": text,
            "created_at": created_at,
            "message": f"Thank you, {name}. Your message has been sent to the shop owner."
        }
    except Exception as e:
        logger.exception("Failed to leave message")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def get_messages() -> dict:
    """Fetch all messages for the owner UI card."""
    logger.info("Service: get_messages called")
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM messages ORDER BY created_at DESC")
        rows = cursor.fetchall()
        msgs = [dict(r) for r in rows]
        return {"status": "success", "messages": msgs}
    except Exception as e:
        logger.exception("Failed to get messages")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def log_call_summary(caller_name: str, caller_role: str, short_summary: str) -> dict:
    """Insert a call record into call_log at call wrap-up."""
    logger.info("Service: log_call_summary for caller='%s'", caller_name)
    conn = sqlite3.connect(str(_DB_PATH))
    try:
        cursor = conn.cursor()
        call_id = f"call_{uuid.uuid4().hex[:8]}"
        call_date = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO call_log (call_id, caller_name, caller_role, call_date, short_summary)
            VALUES (?, ?, ?, ?, ?)
            """,
            (call_id, caller_name.strip(), caller_role.strip(), call_date, short_summary.strip()),
        )
        conn.commit()
        return {
            "status": "success",
            "call_id": call_id,
            "caller_name": caller_name.strip(),
            "caller_role": caller_role.strip(),
            "call_date": call_date,
            "short_summary": short_summary.strip(),
        }
    except Exception as e:
        logger.exception("Failed to log call summary")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def get_call_history(user_role: str = "owner") -> dict:
    """Read call history records (owner-only, most recent first)."""
    logger.info("Service: get_call_history called by role='%s'", user_role)
    if user_role != "owner":
        return {
            "status": "error",
            "message": "Access denied: Only the shop owner can view call history."
        }

    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM call_log ORDER BY call_date DESC")
        rows = cursor.fetchall()
        calls = [dict(r) for r in rows]
        return {"status": "success", "calls": calls}
    except Exception as e:
        logger.exception("Failed to get call history")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def get_customer_history(user_role: str = "owner") -> dict:
    """Read merged customer activity history combining calls and messages (owner-only, most recent first).
    
    Normalizes rows to:
    - type: "call" | "message"
    - name: string
    - timestamp: string
    - summary: string (truncated for messages, full text in full_text)
    """
    logger.info("Service: get_customer_history called by role='%s'", user_role)
    if user_role != "owner":
        return {
            "status": "error",
            "message": "Access denied: Only the shop owner can view customer history."
        }

    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()

        # 1. Fetch calls
        cursor.execute("SELECT * FROM call_log")
        call_rows = cursor.fetchall()

        # 2. Fetch messages
        cursor.execute("SELECT * FROM messages")
        msg_rows = cursor.fetchall()

        combined = []

        for r in call_rows:
            rec = dict(r)
            combined.append({
                "id": rec["call_id"],
                "type": "call",
                "name": rec["caller_name"],
                "role": rec["caller_role"],
                "timestamp": rec["call_date"],
                "summary": rec["short_summary"],
                "full_text": rec["short_summary"],
            })

        for r in msg_rows:
            rec = dict(r)
            raw_text = rec["message_text"]
            words = raw_text.split()
            if len(words) > 15:
                truncated = " ".join(words[:15]) + "..."
            else:
                truncated = raw_text

            combined.append({
                "id": rec["message_id"],
                "type": "message",
                "name": rec["from_name"],
                "role": "customer",
                "timestamp": rec["created_at"],
                "summary": truncated,
                "full_text": raw_text,
            })

        # Sort merged list by timestamp descending (most recent first)
        combined.sort(key=lambda x: x["timestamp"], reverse=True)

        return {
            "status": "success",
            "history": combined,
        }
    except Exception as e:
        logger.exception("Failed to get customer history")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()



def get_daily_summary(date_str: str | None = None) -> dict:
    """Aggregate sales for a given date (defaults to today in UTC or ISO format date).
    
    Returns total amount, transaction count, best-selling item, and sale list.
    """
    logger.info("Service: get_daily_summary called for date_str='%s'", date_str)
    if not date_str:
        target_date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    else:
        target_date = date_str.strip()[:10]

    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = sqlite3.Row
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM sales WHERE sale_date LIKE ? ORDER BY sale_date DESC", (f"{target_date}%",))
        rows = cursor.fetchall()
        
        total_amount = 0.0
        transaction_count = len(rows)
        item_qty_map = {}
        sales_list = []

        for r in rows:
            rec = dict(r)
            amt = float(rec["amount"])
            qty = float(rec["quantity"])
            item = rec["item_name"]
            
            total_amount += amt
            item_qty_map[item] = item_qty_map.get(item, 0.0) + qty
            sales_list.append(rec)

        best_selling_item = None
        if item_qty_map:
            best_selling_item = max(item_qty_map, key=item_qty_map.get)

        return {
            "status": "success",
            "date": target_date,
            "total_amount": total_amount,
            "transaction_count": transaction_count,
            "best_selling_item": best_selling_item or "N/A",
            "sales": sales_list,
        }
    except Exception as e:
        logger.exception("Failed to get daily summary")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def update_shop_hours(hours_text: str, address_text: str, shop_id: str = "primary_shop") -> dict:
    """Update shop hours and address in shop_info (UI-only form target, not exposed as voice tool)."""
    logger.info("Service: update_shop_hours called for shop_id='%s'", shop_id)
    conn = sqlite3.connect(str(_DB_PATH))
    try:
        cursor = conn.cursor()
        now = datetime.now(timezone.utc).isoformat()
        cursor.execute(
            """
            INSERT INTO shop_info (shop_id, hours_text, address_text, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(shop_id) DO UPDATE SET
                hours_text = excluded.hours_text,
                address_text = excluded.address_text,
                updated_at = excluded.updated_at
            """,
            (shop_id, hours_text.strip(), address_text.strip(), now),
        )
        conn.commit()
        return {
            "status": "success",
            "shop_id": shop_id,
            "hours": hours_text.strip(),
            "address": address_text.strip(),
            "updated_at": now,
            "message": "Shop hours and address updated successfully."
        }
    except Exception as e:
        logger.exception("Failed to update shop hours")
        return {"status": "error", "message": str(e)}
    finally:
        conn.close()


def get_market_price(commodity: str, state: str | None = None, market: str | None = None) -> dict:
    """Fetch live market price data from Agmarknet / data.gov.in API with a 5s timeout.

    Reads API key from AGMARKNET_API_KEY environment variable.
    Get a free key at https://data.gov.in/user/register then visit:
    https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi-price
    and click "Get API" to activate the resource for your account.

    Returns commodity, price, market, and actual date of data on success, or clear failure signal.
    Never fabricates price data.
    """
    import urllib.request
    import urllib.parse
    logger.info("Service: get_market_price for commodity='%s', state='%s', market='%s'", commodity, state, market)

    # Read key from environment — never fall back to a public demo key that gets 403'd
    api_key = os.environ.get("AGMARKNET_API_KEY", "").strip()
    if not api_key:
        return {
            "status": "failed",
            "commodity": commodity,
            "message": (
                "AGMARKNET_API_KEY is not set. "
                "Register at https://data.gov.in/user/register, then add "
                "AGMARKNET_API_KEY=your_key to backend/.env.local and restart the server."
            ),
        }

    base_url = "https://api.data.gov.in/resource/9ef84e57-1933-490f-a004-94940974e655"
    params = {
        "api-key": api_key,
        "format": "json",
        "limit": 10,
        "filters[commodity]": commodity.strip(),
    }
    if state and state.strip():
        params["filters[state]"] = state.strip()
    if market and market.strip():
        params["filters[market]"] = market.strip()

    url = f"{base_url}?{urllib.parse.urlencode(params)}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "DukaanMitra/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            raw = resp.read().decode("utf-8")
            if resp.status == 200:
                data = json.loads(raw)
                records = data.get("records", [])
                if records:
                    rec = records[0]
                    modal_price = rec.get("modal_price")
                    max_price = rec.get("max_price")
                    min_price = rec.get("min_price")
                    price_val = modal_price or max_price or min_price or "N/A"
                    unit_str = rec.get("unit") or "Quintal"
                    return {
                        "status": "success",
                        "commodity": rec.get("commodity", commodity),
                        "state": rec.get("state", state or "N/A"),
                        "district": rec.get("district", "N/A"),
                        "market": rec.get("market", market or "N/A"),
                        "price": f"\u20b9{price_val} per {unit_str}",
                        "modal_price": modal_price,
                        "min_price": min_price,
                        "max_price": max_price,
                        "unit": unit_str,
                        "date": (
                            rec.get("arrival_date")
                            or rec.get("reported_date")
                            or datetime.now(timezone.utc).strftime("%Y-%m-%d")
                        ),
                        "raw_record": rec,
                    }
                else:
                    return {
                        "status": "failed",
                        "message": (
                            f"No Agmarknet data found for '{commodity}'"
                            + (f" in {state}" if state else "")
                            + ". Try a different commodity name or leave state blank."
                        ),
                        "commodity": commodity,
                    }
            else:
                return {
                    "status": "failed",
                    "message": f"Agmarknet API returned HTTP {resp.status}.",
                    "commodity": commodity,
                }
    except urllib.error.HTTPError as e:
        if e.code == 403:
            logger.warning("Agmarknet 403 — API key rejected: %s", e)
            return {
                "status": "failed",
                "commodity": commodity,
                "message": (
                    "Agmarknet API key invalid or not yet activated (HTTP 403). "
                    "Visit https://data.gov.in/resource/current-daily-price-various-commodities-various-markets-mandi-price "
                    "and click \"Get API\" to activate the dataset for your account, then update AGMARKNET_API_KEY in backend/.env.local."
                ),
            }
        logger.warning("Agmarknet HTTP error: %s", e)
        return {
            "status": "failed",
            "message": f"Agmarknet API error (HTTP {e.code}). Please try again shortly.",
            "commodity": commodity,
        }
    except TimeoutError:
        logger.warning("Agmarknet API timed out for commodity='%s'", commodity)
        return {
            "status": "failed",
            "message": "Agmarknet API did not respond in time. Please try again in a moment.",
            "commodity": commodity,
        }
    except Exception as e:
        logger.warning("Agmarknet API request failed: %s", e)
        return {
            "status": "failed",
            "message": "Could not reach the Agmarknet API. Check your network connection and try again.",
            "commodity": commodity,
        }


