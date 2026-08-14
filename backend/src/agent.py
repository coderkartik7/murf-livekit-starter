import asyncio
import logging
import uuid

from dotenv import load_dotenv
from livekit import api, rtc
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    room_io,
    tokenize,
)
from livekit.plugins import deepgram, google, murf, noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

import db
import services

logger = logging.getLogger("agent")

load_dotenv(".env.local")
SYSTEM_PROMPT = """
IDENTITY
You are Dukaan Mitra, a voice assistant working on behalf of a small shop owner in India.
You are speaking to a {user_role}.

OBJECTIVES
A successful call does one of the following:
{role_objectives}

KNOWLEDGE
You only know what the shop owner has told you or logged with you directly — stock levels, prices, and hours they've shared in this system. You have no access to real-time stock, competitor pricing, or anything not explicitly provided. When you don't know something, say so plainly instead of guessing.

LANGUAGE & SCRIPT
Respond only in clear Indian English. If the caller speaks Hindi or Hinglish, understand their intent as best you can, but keep your own replies in English — don't switch languages yourself. Match their formality: brief and casual with a vendor/owner, polite and clear with a customer.
Always write every language in its own native script.
- Hindi → Devanagari (नमस्ते), never romanized (never "namaste").
- Apply the same rule to any other non-English language used.

MEMORY
At the start of a conversation, once you know who you're speaking with, use the lookup_caller function to check if they're a returning caller.
- If found: greet them by name and reference something specific from their saved facts (e.g. past orders, preferred delivery slot) to continue naturally from last time.
- If not found: proceed as a first-time interaction.
Before saving any new information about the caller, always ask their permission first — e.g. "Is it okay if I remember this for next time?" Only call save_caller_info if they agree. If they decline, do not save anything, and don't ask again in the same call.

TOOLS
- lookup_product(product_name): Use when a customer asks if a product is in stock, or asks for product price/unit/availability.
- place_order(customer_name, item_name, quantity, delivery_slot, contact_phone): Use when a customer wants to place a new order. Confirm item, quantity, estimated total, and delivery slot before placing order.
- check_order_status(query): Use when a customer asks about their order status, delivery progress, or slot using order ID or phone/user ID.
- escalate_to_returns_specialist(reason): Use only for actual return/refund/dispute requests, NOT general order status questions (those stay with check_order_status on the main agent).
- get_shop_info(): Use when a caller asks about shop opening/closing hours or store address/location.
- log_sale(item_name, quantity, unit, amount): OWNER ONLY. Use when shop owner wants to log a sale. Always confirm parsed values before saving.
- update_stock(item_name, quantity, unit, price): OWNER ONLY. Use when shop owner wants to add stock or log a restock entry for an item. Always confirm parsed details before saving.
- log_credit(customer_name, amount, credit_type, note): OWNER ONLY. Use when shop owner wants to log udhaar given or paid back. Always confirm details before saving.
- check_credit_balance(customer_name): Use to check customer udhaar balance (given - paid).
- leave_message_for_owner(from_name, message_text): Use when a customer wants to leave a message, inquiry, or offline order request for the owner. Always confirm message text before saving.
- get_daily_summary(date): OWNER ONLY. Use to give a spoken recap of daily sales amount, count, and best-selling item.
- get_market_price(commodity, state, market): Use to look up live commodity market prices from Agmarknet API.


GUARDRAILS
- Never confirm a price, discount, delivery time, or stock availability the owner hasn't explicitly told you.
- Never claim an item is "in stock" or "available" unless you actually have that information.
- Never make a business decision on the owner's behalf — no discounts, no credit/udhaar approval, no delivery commitments.
- If asked to do any of the above, use this escalation line: "I can't confirm that myself — let me have the shop owner get back to you on that. Can I take a message?"
- Never invent inventory numbers or shop details you don't have.
- Financial details (profit, margins, earnings, revenue) are confidential business information.
  If anyone other than the shop owner asks about profit, earnings, or margins, do not say you
  don't have the information — say plainly that this is private business information you can't
  share, e.g. "That's private business information, I'm not able to share that."

ESCALATION
Use create_escalation ONLY when a caller reports a payment dispute, refund request, order dispute, or credit/udhaar balance dispute that you cannot resolve yourself. Do NOT use it for normal questions like product availability, shop hours, or general queries.

Before calling create_escalation, you MUST:
1. Tell the caller exactly what you plan to include in the summary — issue type, a brief description of their concern, urgency level, and how they prefer to be contacted.
2. Ask explicitly: "Is it okay if I log this for the owner with those details?"
3. Only proceed if they clearly agree. If they say no or are unsure, do not create an escalation.

Privacy rules — NEVER include any of the following in the summary field:
- OTPs, PINs, or passwords
- Full bank account or card numbers
- Any sensitive personal authentication data

After creating the escalation:
- Tell the caller their reference ID (e.g. "Your reference number is ESC_AB12").
- Say the shop owner will follow up with them.
- Do NOT promise any specific timeframe for follow-up.

STYLE
Keep replies to one or two short sentences — this is spoken audio, not a chat window. No lists, no bullet points, no brackets, no sentence over about 20 words. Always confirm what you understood before treating an update as final. If the user goes quiet, gently check in rather than staying silent.
"""

OWNER_OBJECTIVES = """1. A vendor/owner logs a sale or stock update, and you confirm it back accurately before treating it as done.
2. If they ask for business-related details (like shop hours, logged udhaar, summaries), help them query it or update it.
3. Be friendly, brief, and highly functional for shop operations."""

CUSTOMER_OBJECTIVES = """1. A customer can place a new order using the place_order tool, check product availability, price, order status, or shop hours.
2. If placing an order or asking a question outside catalog info, confirm details with caller and place the order or take a message for the owner using leave_message_for_owner.
3. Let them leave a message or inquiry if they want the owner to follow up directly."""

OUTBOUND_GREETING = """Namaste! This is Dukaan Mitra, calling on behalf of your shop.
I'm calling because {item} is running low on stock. If you'd like me to stop these calls, just say stop.
 Do you want me to note this as a restock reminder?"""


async def make_outbound_call(
    phone_number: str, room_name: str, item_name: str = "an item"
):
    lkapi = api.LiveKitAPI()

    await lkapi.agent_dispatch.create_dispatch(
        api.CreateAgentDispatchRequest(
            agent_name="my-agent",
            room=room_name,
            metadata=item_name,
        )
    )

    await lkapi.sip.create_sip_participant(
        api.CreateSIPParticipantRequest(
            sip_trunk_id="ST_e7MNaacTy4sE",
            sip_call_to=phone_number,
            room_name=room_name,
            participant_identity="outbound-call",
        )
    )
    await lkapi.aclose()


class Assistant(Agent):
    def __init__(
        self, instructions: str = SYSTEM_PROMPT, user_role: str = "customer"
    ) -> None:
        super().__init__(instructions=instructions)
        self.user_role = user_role
        # Incremented by every @function_tool to signal a productive session
        self._tools_called: int = 0
        self._tool_error: bool = False
        self._failure_reason: str | None = None
        self._end_state: str | None = None
        self._order_placed: bool = False
        self._business_success: bool = False
        self._order_id: str | None = None

    @function_tool
    async def lookup_caller(self, context: RunContext, user_id: str):
        """Look up a returning caller's saved info by their user ID.
        Call this early in the conversation once you have identified
        who you're speaking with, to check if they're a returning caller.

        Args:
            user_id: Caller identifier — phone number or normalized name
                     (lowercased, spaces replaced with underscores).
        """
        self._tools_called += 1
        logger.info("Looking up caller: %s", user_id)
        record = await db.get_caller(user_id)
        if record:
            logger.info("Found returning caller: %s", user_id)
            return record
        logger.info("Caller not found: %s", user_id)
        return {"status": "not_found", "message": "No saved info for this caller."}

    @function_tool
    async def save_caller_info(
        self,
        context: RunContext,
        user_id: str,
        name: str,
        role: str,
        language_preference: str,
        facts_json: str,
    ):
        """Save or update what you've learned about this caller.
        Only call this AFTER the caller has explicitly agreed to let
        you remember the information.

        Args:
            user_id: Caller identifier — phone number or normalized name
                     (lowercased, spaces replaced with underscores).
            name: The caller's display name.
            role: Either "owner" or "customer".
            language_preference: The caller's preferred language.
            facts_json: JSON string of learned facts — e.g. '{"past_orders": [], "preferred_delivery_slot": "Morning"}'
        """
        import json

        self._tools_called += 1
        logger.info("Saving caller info for: %s", user_id)
        try:
            facts = json.loads(facts_json)
        except Exception:
            facts = {}
        await db.upsert_caller(user_id, name, role, language_preference, facts)
        return {"status": "saved", "user_id": user_id}

    @function_tool
    async def get_shop_status(self, context: RunContext, shop_id: str = "primary_shop"):
        """Retrieve the hours and address of a shop.

        Args:
            shop_id: Unique identifier for the shop (e.g. 'primary_shop').
        """
        import services

        self._tools_called += 1
        logger.info("Tool: get_shop_status called for shop_id=%s", shop_id)
        return services.get_shop_status(shop_id)

    @function_tool
    async def get_shop_info(self, context: RunContext):
        """Retrieve shop operating hours and physical store location/address."""
        import services

        self._tools_called += 1
        logger.info("Tool: get_shop_info called")
        return services.get_shop_info()

    @function_tool
    async def lookup_product(self, context: RunContext, product_name: str):
        """Look up a product's price, unit size, and stock availability by name.

        Args:
            product_name: Name of the product or item to search for (e.g. 'milk', 'bread', 'rice').
        """
        import services

        self._tools_called += 1
        logger.info("Tool: lookup_product called for product_name=%s", product_name)
        return services.lookup_product(product_name)

    @function_tool
    async def place_order(
        self,
        context: RunContext,
        customer_name: str,
        item_name: str,
        quantity: float,
        delivery_slot: str = "Standard Delivery",
        contact_phone: str = "",
    ):
        """Place a new order for a customer.
        Use when a caller/customer wants to order or buy products from the shop.
        Always confirm item name, quantity, estimated total, and delivery slot with the caller before calling this tool.

        Args:
            customer_name: Name of the customer placing the order.
            item_name: Product name to order (e.g. 'Milk', 'Rice', 'Refined Oil 1L').
            quantity: Quantity to order (e.g. 1, 2, 5).
            delivery_slot: Preferred delivery timing (e.g. 'Morning (8 AM - 10 AM)', 'Evening (6 PM - 8 PM)').
            contact_phone: Optional phone number or contact identifier.
        """
        import services

        self._tools_called += 1
        logger.info(
            "Tool: place_order called for customer=%s, item=%s, qty=%s",
            customer_name,
            item_name,
            quantity,
        )
        try:
            res = services.place_order(
                customer_name=customer_name,
                item_name=item_name,
                quantity=quantity,
                delivery_slot=delivery_slot,
                contact_phone=contact_phone,
            )
            if isinstance(res, dict) and res.get("status") == "error":
                logger.error("Tool: place_order returned error: %s", res.get("message"))
                self._tool_error = True
                self._failure_reason = "tool_error"
            else:
                self._order_placed = True
                self._business_success = True
                self._order_id = res.get("order_id")
                self._end_state = "order_placed"
                logger.info(
                    "Tool: place_order succeeded. Generated order_id=%s", self._order_id
                )
            return res
        except Exception as e:
            logger.exception(
                "Tool: place_order failed for customer=%s: %s", customer_name, e
            )
            self._tool_error = True
            self._failure_reason = "tool_error"
            return {"status": "error", "message": f"Failed to place order: {e!s}"}

    @function_tool
    async def check_order_status(self, context: RunContext, query: str):
        """Check order status and delivery slot for an order ID or customer user ID.

        Args:
            query: Order ID (e.g. 'ord_001') or customer ID / phone number (e.g. 'user_rahul').
        """
        import services

        self._tools_called += 1
        logger.info("Tool: check_order_status called for query=%s", query)
        return services.check_order_status(query)

    @function_tool
    async def log_sale(
        self,
        context: RunContext,
        item_name: str,
        quantity: float,
        unit: str,
        amount: float,
    ):
        """Log a completed sale into the sales ledger. OWNER ONLY.
        Always confirm parsed item name, quantity, unit, and total amount with the caller before calling this tool.

        Args:
            item_name: Name of the item sold (e.g. 'Rice', 'Milk').
            quantity: Quantity sold (e.g. 2, 0.5).
            unit: Unit of measurement (e.g. 'kg', 'packet', 'liter').
            amount: Total sale amount in Rupees (e.g. 120.0).
        """
        import services

        self._tools_called += 1
        logger.info(
            "Tool: log_sale called for item=%s, qty=%s, amount=%s",
            item_name,
            quantity,
            amount,
        )
        res = services.log_sale(
            item_name, quantity, unit, amount, user_role=self.user_role
        )
        if isinstance(res, dict) and res.get("status") == "error":
            logger.error("Tool: log_sale returned error: %s", res.get("message"))
            self._tool_error = True
            self._failure_reason = "tool_error"
        else:
            self._business_success = True
            self._end_state = "sale_logged"
        return res

    @function_tool
    async def update_stock(
        self,
        context: RunContext,
        item_name: str,
        quantity: float,
        unit: str = "",
        price: float = 0.0,
    ):
        """Add stock / log a restock entry for an item in inventory. OWNER ONLY.
        Always confirm parsed item name, quantity, and unit with the caller before calling this tool.

        Args:
            item_name: Name of the product or item to restock (e.g. 'Refined Oil 1L', 'Rice').
            quantity: Quantity to add to stock (e.g. 100, 10).
            unit: Unit of measurement (e.g. 'liter', 'kg', 'packet', 'unit').
            price: Optional unit price in Rupees if updating or adding price.
        """
        import services

        self._tools_called += 1
        logger.info(
            "Tool: update_stock called for item='%s', qty=%s, unit='%s'",
            item_name,
            quantity,
            unit,
        )
        try:
            res = services.update_stock(
                item_name=item_name,
                quantity=quantity,
                unit=unit,
                price=price,
                user_role=self.user_role,
            )
            if isinstance(res, dict) and res.get("status") == "error":
                logger.error(
                    "Tool: update_stock returned error status: %s", res.get("message")
                )
                self._tool_error = True
                self._failure_reason = "tool_error"
            else:
                self._business_success = True
                self._end_state = "stock_updated"
            return res
        except Exception as e:
            logger.exception(
                "Tool: update_stock failed with exception for item='%s': %s",
                item_name,
                e,
            )
            self._tool_error = True
            self._failure_reason = "tool_error"
            return {
                "status": "error",
                "message": f"Failed to update stock for {item_name}: {e!s}",
            }

    @function_tool
    async def log_credit(
        self,
        context: RunContext,
        customer_name: str,
        amount: float,
        credit_type: str,
        note: str = "",
    ):
        """Log a customer credit ('udhaar') entry — either credit given or repayment paid. OWNER ONLY.
        Always confirm customer name, amount, and whether it was given or paid with the caller before calling this tool.

        Args:
            customer_name: Customer's name (e.g. 'Ramesh', 'Rahul').
            amount: Credit amount in Rupees (e.g. 500.0).
            credit_type: 'given' (owner lent goods on credit) or 'paid' (customer paid back).
            note: Optional note (e.g. 'Groceries purchase', 'UPI payment').
        """
        import services

        self._tools_called += 1
        logger.info(
            "Tool: log_credit called for customer=%s, amt=%s, type=%s",
            customer_name,
            amount,
            credit_type,
        )
        return services.log_credit(
            customer_name, amount, credit_type, note, user_role=self.user_role
        )

    @function_tool
    async def check_credit_balance(self, context: RunContext, customer_name: str):
        """Check current udhaar credit balance and transaction summary for a customer.

        Args:
            customer_name: Customer's name to query credit balance for.
        """
        import services

        self._tools_called += 1
        logger.info("Tool: check_credit_balance called for customer=%s", customer_name)
        return services.check_credit_balance(customer_name)

    @function_tool
    async def leave_message_for_owner(
        self, context: RunContext, from_name: str, message_text: str
    ):
        """Leave a message, inquiry, or order request for the shop owner.
        Always confirm caller name and the message text with the caller before calling this tool.

        Args:
            from_name: Name of the caller leaving the message (defaults to 'Unknown' if not provided).
            message_text: The message or inquiry content to deliver to the owner.
        """
        import services

        self._tools_called += 1
        logger.info("Tool: leave_message_for_owner called from=%s", from_name)
        res = services.leave_message_for_owner(from_name, message_text)
        if isinstance(res, dict) and res.get("status") == "error":
            logger.error(
                "Tool: leave_message_for_owner returned error: %s", res.get("message")
            )
            self._tool_error = True
            self._failure_reason = "tool_error"
        else:
            self._business_success = True
            self._end_state = "enquiry_logged"
        return res

    @function_tool
    async def get_daily_summary(self, context: RunContext, date: str = ""):
        """Get daily sales aggregate summary including total revenue, transaction count, and top item.

        Args:
            date: Optional date string in YYYY-MM-DD format (defaults to today).
        """
        import services

        self._tools_called += 1
        logger.info("Tool: get_daily_summary called for date=%s", date)
        return services.get_daily_summary(date)

    @function_tool
    async def get_market_price(
        self, context: RunContext, commodity: str, state: str = "", market: str = ""
    ):
        """Fetch live commodity market price trends from Agmarknet API.

        Args:
            commodity: Name of agricultural commodity (e.g. 'Rice', 'Potato', 'Wheat', 'Onion').
            state: Optional Indian state name (e.g. 'Delhi', 'Punjab').
            market: Optional market center name.
        """
        import services

        self._tools_called += 1
        logger.info("Tool: get_market_price called for commodity=%s", commodity)
        return services.get_market_price(commodity, state, market)

    @function_tool
    async def create_escalation(
        self,
        context: RunContext,
        caller_name: str,
        issue_type: str,
        summary: str,
        urgency: str,
        language: str,
        contact_method: str,
    ):
        """Escalate an unresolved dispute to the shop owner for human follow-up.
        Call this when a caller reports a payment dispute, refund request, order dispute,
        or credit/udhaar balance dispute you cannot resolve yourself — NOT for normal questions.
        BEFORE calling this tool, tell the caller what you will include in the summary and
        ask for their explicit permission. Only call this tool after they agree.
        Never include OTPs, PINs, passwords, or account numbers in the summary.

        Args:
            caller_name: Name of the caller raising the dispute.
            issue_type: Category of the issue — one of: 'payment_dispute', 'refund_request',
                        'order_dispute', 'udhaar_dispute'.
            summary: Brief, factual description of the issue. No sensitive auth data.
            urgency: Urgency level — 'low', 'medium', or 'high'.
            language: Language the caller spoke in (e.g. 'English', 'Hindi').
            contact_method: How the owner should reach the caller (e.g. 'phone callback', 'WhatsApp').
        """
        import services

        self._tools_called += 1
        logger.info(
            "Tool: create_escalation called for caller=%s, issue=%s, urgency=%s",
            caller_name,
            issue_type,
            urgency,
        )
        return services.create_escalation(
            caller_name=caller_name,
            issue_type=issue_type,
            summary=summary,
            urgency=urgency,
            language=language,
            contact_method=contact_method,
        )

    @function_tool
    async def escalate_to_returns_specialist(self, context: RunContext, reason: str):
        """use only for actual return/refund/dispute requests, NOT general order status questions (those stay with check_order_status on the main agent).

        Args:
            reason: The reason or context for the return, refund, or order dispute request.
        """
        self._tools_called += 1
        logger.info(
            "Tool: escalate_to_returns_specialist called with reason=%s", reason
        )
        await context.session.say("I'll connect you to our returns specialist.")
        specialist = ReturnsSpecialist(reason=reason, user_role=self.user_role)
        context.session.update_agent(specialist)
        return "Connected to returns specialist."


RETURNS_SPECIALIST_PROMPT = """
IDENTITY
You are the Returns and Refunds Specialist for Dukaan Mitra.
You have been handed off a customer request for a return, refund, or order dispute.

HANDOFF REASON / CONTEXT:
"{reason}"

OBJECTIVES
1. Focus ONLY on returns, refunds, and order disputes. Do not ask the customer to repeat the basic issue they already stated.
2. Use check_order_status to look up the order in question using the order ID or customer details.
3. If the issue remains unresolved or the order cannot be found, use create_escalation to log an escalation for the shop owner.

KNOWLEDGE
You only know what the shop owner has told you or logged with you directly — stock levels, prices, and hours they've shared in this system. You have no access to real-time stock, competitor pricing, or anything not explicitly provided. When you don't know something, say so plainly instead of guessing.

LANGUAGE & SCRIPT
Respond only in clear Indian English. If the caller speaks Hindi or Hinglish, understand their intent as best you can, but keep your own replies in English — don't switch languages yourself. Match their formality: polite and clear with a customer.
Always write every language in its own native script.
- Hindi → Devanagari (नमस्ते), never romanized (never "namaste").
- Apply the same rule to any other non-English language used.

GUARDRAILS
- Never confirm a price, discount, delivery time, or stock availability the owner hasn't explicitly told you.
- Never claim an item is "in stock" or "available" unless you actually have that information.
- Never make a business decision on the owner's behalf — no discounts, no credit/udhaar approval, no delivery commitments.
- If asked to do any of the above, use this escalation line: "I can't confirm that myself — let me have the shop owner get back to you on that. Can I take a message?"
- Never invent inventory numbers or shop details you don't have.
- Financial details (profit, margins, earnings, revenue) are confidential business information.

ESCALATION
Use create_escalation ONLY when a caller reports a payment dispute, refund request, order dispute, or credit/udhaar balance dispute that you cannot resolve yourself. Do NOT use it for normal questions like product availability, shop hours, or general queries.

Before calling create_escalation, you MUST:
1. Tell the caller exactly what you plan to include in the summary — issue type, a brief description of their concern, urgency level, and how they prefer to be contacted.
2. Ask explicitly: "Is it okay if I log this for the owner with those details?"
3. Only proceed if they clearly agree. If they say no or are unsure, do not create an escalation.

Privacy rules — NEVER include any of the following in the summary field:
- OTPs, PINs, or passwords
- Full bank account or card numbers
- Any sensitive personal authentication data

After creating the escalation:
- Tell the caller their reference ID (e.g. "Your reference number is ESC_AB12").
- Say the shop owner will follow up with them.
- Do NOT promise any specific timeframe for follow-up.

STYLE
Keep replies to one or two short sentences — this is spoken audio, not a chat window. No lists, no bullet points, no brackets, no sentence over about 20 words. Always confirm what you understood before treating an update as final. If the user goes quiet, gently check in rather than staying silent.
"""


class ReturnsSpecialist(Agent):
    def __init__(self, reason: str = "", user_role: str = "customer") -> None:
        instructions = RETURNS_SPECIALIST_PROMPT.format(reason=reason)
        super().__init__(instructions=instructions)
        self.reason = reason
        self.user_role = user_role
        self._tools_called: int = 0
        self._tool_error: bool = False
        self._failure_reason: str | None = None
        self._end_state: str | None = None
        self._business_success: bool = False

    async def on_enter(self) -> None:
        await self.session.say(
            "Hi, I'm the returns and refunds specialist — let's sort out your order issue."
        )

    @function_tool
    async def check_order_status(self, context: RunContext, query: str):
        """Check order status and delivery slot for an order ID or customer user ID.

        Args:
            query: Order ID (e.g. 'ord_001') or customer ID / phone number (e.g. 'user_rahul').
        """
        import services

        self._tools_called += 1
        logger.info(
            "ReturnsSpecialist: Tool check_order_status called for query=%s", query
        )
        res = services.check_order_status(query)
        if isinstance(res, dict) and res.get("status") == "success":
            self._business_success = True
            self._end_state = "order_status_checked"
        return res

    @function_tool
    async def create_escalation(
        self,
        context: RunContext,
        caller_name: str,
        issue_type: str,
        summary: str,
        urgency: str,
        language: str,
        contact_method: str,
    ):
        """Escalate an unresolved dispute to the shop owner for human follow-up.
        Call this when a caller reports a payment dispute, refund request, order dispute,
        or credit/udhaar balance dispute you cannot resolve yourself — NOT for normal questions.
        BEFORE calling this tool, tell the caller what you will include in the summary and
        ask for their explicit permission. Only call this tool after they agree.
        Never include OTPs, PINs, passwords, or account numbers in the summary.

        Args:
            caller_name: Name of the caller raising the dispute.
            issue_type: Category of the issue — one of: 'payment_dispute', 'refund_request',
                        'order_dispute', 'udhaar_dispute'.
            summary: Brief, factual description of the issue. No sensitive auth data.
            urgency: Urgency level — 'low', 'medium', or 'high'.
            language: Language the caller spoke in (e.g. 'English', 'Hindi').
            contact_method: How the owner should reach the caller (e.g. 'phone callback', 'WhatsApp').
        """
        import services

        self._tools_called += 1
        logger.info(
            "ReturnsSpecialist: Tool create_escalation called for caller=%s, issue=%s, urgency=%s",
            caller_name,
            issue_type,
            urgency,
        )
        res = services.create_escalation(
            caller_name=caller_name,
            issue_type=issue_type,
            summary=summary,
            urgency=urgency,
            language=language,
            contact_method=contact_method,
        )
        if isinstance(res, dict) and res.get("status") == "success":
            self._business_success = True
            self._end_state = "escalation_created"
        return res


server = AgentServer()


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()
    db.init_db()


server.setup_fnc = prewarm


@server.rtc_session(agent_name="my-agent")
async def my_agent(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    # Join the room and connect to the user first so participants is populated
    await ctx.connect()

    # --- Call tracking: generate call_id and detect channel ---
    call_id = f"call_{uuid.uuid4().hex[:12]}"
    from datetime import datetime, timezone

    call_started_at = datetime.now(timezone.utc).isoformat()

    # Detect channel: SIP participant = 'sip', anything else = 'web'
    channel = "web"
    for p in ctx.room.remote_participants.values():
        if p.kind == rtc.ParticipantKind.PARTICIPANT_KIND_SIP:
            channel = "sip"
            break

    # Write start row immediately (outcome defaults to 'failed' as a safe baseline)
    try:
        await db.insert_call_start(call_id, channel, call_started_at)
    except Exception:
        logger.exception("Failed to insert call start record")

    # Extract user role from participant metadata
    user_role = "customer"
    for participant in ctx.room.remote_participants.values():
        if (
            participant.identity.startswith("voice_assistant_user_")
            and participant.metadata
        ):
            user_role = participant.metadata
            break

    if ctx.job.metadata:
        greet_inst = f"Greet as Dukaan Mitra calling the shop owner. In the first two sentences say who is calling, why (that {ctx.job.metadata} is running low on stock), and that they can say 'stop' to end these calls. Then ask if they'd like it noted as a restock reminder."
        role_obj = OWNER_OBJECTIVES
        user_label = "shop owner"

    # Format objectives based on role
    elif user_role == "owner":
        role_obj = OWNER_OBJECTIVES
        user_label = "shop owner"
        greet_inst = "Greet the user as Dukaan Mitra, briefly explain you help them run the shop by logging sales, tracking stock, and managing customer udhaar, then ask how you can help them today. Keep it short."
    else:
        role_obj = CUSTOMER_OBJECTIVES
        user_label = "customer"
        greet_inst = "Greet the user as Dukaan Mitra, explain you are the shop's voice assistant here to check item availability, shop hours, or take a message for the owner. Ask how you can help them today. Keep it short."

    formatted_instructions = SYSTEM_PROMPT.format(
        user_role=user_label, role_objectives=role_obj
    )

    # Set up a voice AI pipeline using Murf Falcon, Gemini, Deepgram, and the LiveKit turn detector
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt=deepgram.STT(model="nova-3", language="multi"),
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=google.LLM(
            model="gemini-3.5-flash-lite",
        ),
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts=murf.TTS(
            voice="Anisha",
            style="Conversation",
            tokenizer=tokenize.basic.SentenceTokenizer(min_sentence_len=2),
            text_pacing=True,
        ),
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
    )

    # To use a realtime model instead of a voice pipeline, use the following session setup instead.
    # (Note: This is for the OpenAI Realtime API. For other providers, see https://docs.livekit.io/agents/models/realtime/))
    # 1. Install livekit-agents[openai]
    # 2. Set OPENAI_API_KEY in .env.local
    # 3. Add `from livekit.plugins import openai` to the top of this file
    # 4. Use the following session setup instead of the version above
    # session = AgentSession(
    #     llm=openai.realtime.RealtimeModel(voice="marin")
    # )

    # # Add a virtual avatar to the session, if desired
    # # For other providers, see https://docs.livekit.io/agents/models/avatar/
    # avatar = hedra.AvatarSession(
    #   avatar_id="...",  # See https://docs.livekit.io/agents/models/avatar/plugins/hedra
    # )
    # # Start the avatar and wait for it to join
    # await avatar.start(session, room=ctx.room)

    agent = Assistant(instructions=formatted_instructions, user_role=user_role)

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=agent,
        room=ctx.room,
        room_options=room_io.RoomOptions(
            audio_input=room_io.AudioInputOptions(
                noise_cancellation=lambda params: (
                    noise_cancellation.BVCTelephony()
                    if params.participant.kind
                    == rtc.ParticipantKind.PARTICIPANT_KIND_SIP
                    else noise_cancellation.BVC()
                ),
            ),
        ),
    )

    disconnected_event = asyncio.Event()

    @ctx.room.on("disconnected")
    def on_room_disconnected(*args):
        logger.info("Room disconnected event received for call_id=%s", call_id)
        disconnected_event.set()

    try:
        await session.generate_reply(instructions=greet_inst)
        # Keep agent entrypoint active until caller hangs up / room disconnects
        if ctx.room.isconnected:
            await disconnected_event.wait()
    finally:
        # --- Call outcome tracking (evaluates ONCE after call actually ends) ---

        # --- Call outcome tracking ---
        from datetime import datetime, timezone

        call_ended_at = datetime.now(timezone.utc).isoformat()
        started_dt = datetime.fromisoformat(call_started_at)
        ended_dt = datetime.fromisoformat(call_ended_at)
        duration_sec = int((ended_dt - started_dt).total_seconds())

        current_agent = getattr(session, "current_agent", None) or agent

        agents_to_check = [agent]
        if current_agent and current_agent is not agent:
            agents_to_check.append(current_agent)

        tools_used = sum(getattr(a, "_tools_called", 0) for a in agents_to_check)
        end_state = getattr(current_agent, "_end_state", None) or getattr(
            agent, "_end_state", None
        )
        order_placed = any(getattr(a, "_order_placed", False) for a in agents_to_check)
        order_id = next(
            (
                getattr(a, "_order_id", None)
                for a in agents_to_check
                if getattr(a, "_order_id", None)
            ),
            None,
        )
        business_success = any(
            getattr(a, "_business_success", False) for a in agents_to_check
        )
        tool_error = any(getattr(a, "_tool_error", False) for a in agents_to_check)
        last_failure_reason = getattr(
            current_agent, "_failure_reason", None
        ) or getattr(agent, "_failure_reason", None)

        if order_placed or order_id is not None or business_success or end_state in (
            "order_placed",
            "enquiry_logged",
            "escalation_created",
            "sale_logged",
            "stock_updated",
            "order_status_checked",
        ):
            outcome = "success"
            failure_reason = None
        elif tool_error and not (order_placed or business_success):
            outcome = "failed"
            failure_reason = last_failure_reason or "tool_error"
        elif isinstance(current_agent, ReturnsSpecialist) and not business_success:
            outcome = "failed"
            failure_reason = "unresolved_dispute"
        elif tools_used > 0:
            outcome = "success"
            failure_reason = None
        elif duration_sec < 5:
            outcome = "failed"
            failure_reason = "no_response"
        else:
            outcome = "failed"
            failure_reason = "hangup"

        logger.info(
            "Call Outcome Decision Diagnostic: call_id=%s | order_placed=%s (order_id=%s) | business_success=%s | end_state=%s | tools_used=%d | tool_error=%s | failure_reason=%s | duration=%ds => DETERMINED OUTCOME=%s",
            call_id,
            order_placed,
            order_id,
            business_success,
            end_state,
            tools_used,
            tool_error,
            failure_reason,
            duration_sec,
            outcome,
        )

        try:
            await db.update_call_end(
                call_id, call_ended_at, duration_sec, outcome, failure_reason
            )
            logger.info(
                "Logged call outcome: call_id=%s outcome=%s tools_used=%d duration=%ds",
                call_id,
                outcome,
                tools_used,
                duration_sec,
            )
        except Exception:
            logger.exception("Failed to update call end record")

        # Automatic call summary logging at call wrap-up
        try:
            summary_text = f"Voice session completed for {user_label}."
            services.log_call_summary(
                caller_name="Shop Owner" if user_role == "owner" else "Customer",
                caller_role=user_role,
                short_summary=summary_text,
            )
            logger.info("Automatically logged call summary for role=%s", user_role)
        except Exception as e:
            logger.exception("Failed to log automatic call summary: %s", e)


if __name__ == "__main__":
    cli.run_app(server)
