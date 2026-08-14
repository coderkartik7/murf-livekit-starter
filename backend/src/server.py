from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pathlib import Path
from pydantic import BaseModel, Field
from typing import Optional
import uvicorn
import services
import db

app = FastAPI(title="DukaanMitra API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

_SRC_DIR = Path(__file__).resolve().parent


# ── Pydantic models ────────────────────────────────────────────────────────────

class SaleRequest(BaseModel):
    item_name: str
    quantity: float
    unit: str
    amount: float
    user_role: str = "owner"


class CreditRequest(BaseModel):
    customer_name: str
    amount: float
    credit_type: str = Field(..., alias="type")
    note: Optional[str] = ""
    user_role: str = "owner"


class MessageRequest(BaseModel):
    from_name: Optional[str] = "Unknown"
    message_text: str
    from_user_id: Optional[str] = "customer_anon"


class ShopHoursRequest(BaseModel):
    hours_text: str
    address_text: str
    shop_id: str = "primary_shop"


# ── Startup ───────────────────────────────────────────────────────────────────

@app.on_event("startup")
def startup_event():
    db.init_db()


# ── Shop ──────────────────────────────────────────────────────────────────────

@app.get("/api/shop-status")
def shop_status(shop_id: str = "primary_shop"):
    """Fetch status for the specified shop_id."""
    result = services.get_shop_status(shop_id)
    if result.get("status") == "error":
        raise HTTPException(status_code=404, detail=result.get("message"))
    return result


@app.get("/api/shop/info")
def shop_info():
    """Fetch shop hours and address."""
    return services.get_shop_info()


@app.post("/api/shop/hours")
def update_shop_hours_endpoint(req: ShopHoursRequest):
    return services.update_shop_hours(
        hours_text=req.hours_text,
        address_text=req.address_text,
        shop_id=req.shop_id,
    )


class StockUpdateRequest(BaseModel):
    item_name: str
    quantity: float
    unit: Optional[str] = ""
    price: Optional[float] = 0.0
    user_role: str = "owner"


# ── Products ──────────────────────────────────────────────────────────────────

@app.get("/api/products/lookup")
def product_lookup(name: str = Query(..., description="Product name or query")):
    return services.lookup_product(name)


@app.post("/api/stock/update")
def update_stock_endpoint(req: StockUpdateRequest):
    return services.update_stock(
        item_name=req.item_name,
        quantity=req.quantity,
        unit=req.unit or "",
        price=req.price or 0.0,
        user_role=req.user_role,
    )



class OrderPlaceRequest(BaseModel):
    customer_name: str
    item_name: str
    quantity: float
    delivery_slot: Optional[str] = "Standard Delivery"
    contact_phone: Optional[str] = ""
    user_id: Optional[str] = ""


@app.get("/api/orders/all")
def get_all_orders_endpoint():
    """Fetch all placed orders."""
    return services.get_all_orders()


@app.get("/api/orders/status")
def order_status(query: str = Query(..., description="Order ID or Customer User ID")):
    return services.check_order_status(query)



@app.post("/api/orders/place")
def place_order_endpoint(req: OrderPlaceRequest):
    return services.place_order(
        customer_name=req.customer_name,
        item_name=req.item_name,
        quantity=req.quantity,
        delivery_slot=req.delivery_slot or "Standard Delivery",
        contact_phone=req.contact_phone or "",
        user_id=req.user_id or "",
    )



# ── Sales ─────────────────────────────────────────────────────────────────────

@app.post("/api/sales/log")
def log_sale_endpoint(req: SaleRequest):
    return services.log_sale(
        item_name=req.item_name,
        quantity=req.quantity,
        unit=req.unit,
        amount=req.amount,
        user_role=req.user_role,
    )


# ── Credit / Udhaar ───────────────────────────────────────────────────────────

@app.post("/api/credit/log")
def log_credit_endpoint(req: CreditRequest):
    return services.log_credit(
        customer_name=req.customer_name,
        amount=req.amount,
        credit_type=req.credit_type,
        note=req.note or "",
        user_role=req.user_role,
    )


@app.get("/api/credit/balance")
def check_credit_balance_endpoint(customer_name: str = Query(..., description="Customer Name")):
    return services.check_credit_balance(customer_name)


@app.get("/api/credit/all")
def get_all_credit_balances_endpoint():
    return services.get_all_credit_balances()


# ── Messages ──────────────────────────────────────────────────────────────────

@app.post("/api/messages/leave")
def leave_message_endpoint(req: MessageRequest):
    return services.leave_message_for_owner(
        from_name=req.from_name or "Unknown",
        message_text=req.message_text,
        from_user_id=req.from_user_id or "customer_anon",
    )


@app.get("/api/messages/all")
def get_messages_endpoint():
    return services.get_messages()


# ── Call history (legacy call_log table) ──────────────────────────────────────

@app.get("/api/calls/history")
def get_call_history_endpoint(user_role: str = Query("owner", description="Caller role")):
    return services.get_call_history(user_role=user_role)


@app.get("/api/customer/history")
def get_customer_history_endpoint(user_role: str = Query("owner", description="Caller role")):
    return services.get_customer_history(user_role=user_role)


# ── Daily summary ─────────────────────────────────────────────────────────────

@app.get("/api/daily-summary")
def get_daily_summary_endpoint(date: Optional[str] = Query(None, description="Date in YYYY-MM-DD format")):
    return services.get_daily_summary(date_str=date)


# ── Market price ──────────────────────────────────────────────────────────────

@app.get("/api/market-price")
def get_market_price_endpoint(
    commodity: str = Query(..., description="Commodity name (e.g. Rice, Potato, Wheat)"),
    state: Optional[str] = Query(None),
    market: Optional[str] = Query(None),
):
    return services.get_market_price(commodity=commodity, state=state, market=market)


# ── Escalations ───────────────────────────────────────────────────────────────

@app.get("/api/escalations")
def get_escalations_endpoint():
    """List all escalations, most recent first."""
    return services.get_escalations()


# ── Dashboard API ─────────────────────────────────────────────────────────────

@app.get("/api/calls/stats")
def get_call_stats_endpoint():
    """Aggregate call outcome stats for the dashboard (no PII)."""
    return services.get_call_stats()


@app.get("/api/calls/recent")
def get_recent_calls_endpoint(limit: int = Query(50, ge=1, le=200)):
    """Recent calls list: time, channel, duration, outcome only (no PII)."""
    return services.get_recent_calls(limit=limit)


@app.get("/dashboard", response_class=FileResponse)
def serve_dashboard():
    """Serve the self-contained call outcome dashboard HTML page."""
    html_path = _SRC_DIR / "dashboard.html"
    if not html_path.exists():
        raise HTTPException(status_code=404, detail="dashboard.html not found")
    return FileResponse(str(html_path), media_type="text/html")


if __name__ == "__main__":
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True)
