import logging

from dotenv import load_dotenv
from livekit import rtc, api
from livekit.agents import (
    Agent,
    AgentServer,
    AgentSession,
    JobContext,
    JobProcess,
    RunContext,
    cli,
    function_tool,
    inference,
    tokenize,
    room_io,
)
from livekit.plugins import murf, silero, google, deepgram, noise_cancellation
from livekit.plugins.turn_detector.multilingual import MultilingualModel
import services

import db

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
- check_order_status(query): Use when a customer asks about their order status, delivery progress, or slot using order ID or phone/user ID.
- get_shop_info(): Use when a caller asks about shop opening/closing hours or store address/location.
- log_sale(item_name, quantity, unit, amount): OWNER ONLY. Use when shop owner wants to log a sale. Always confirm parsed values before saving.
- log_credit(customer_name, amount, credit_type, note): OWNER ONLY. Use when shop owner wants to log udhaar given or paid back. Always confirm details before saving.
- check_credit_balance(customer_name): Use to check customer udhaar balance (given - paid).
- leave_message_for_owner(from_name, message_text): Use when a customer wants to leave a message for the owner. Always confirm message text before saving.
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

CUSTOMER_OBJECTIVES = """1. A customer gets an accurate answer about product availability, price, or shop hours — or is told honestly that you don't know and the owner will follow up.
2. Any request outside what the owner has explicitly told you (discounts, delivery promises, order confirmations) is politely deferred, never guessed.
3. Let them leave a message if they want to get in touch with the shop owner."""

OUTBOUND_GREETING = """Namaste! This is Dukaan Mitra, calling on behalf of your shop.
I'm calling because {item} is running low on stock. If you'd like me to stop these calls, just say stop. 
 Do you want me to note this as a restock reminder?"""

async def make_outbound_call(phone_number: str, room_name: str, item_name: str = "an item"):
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
    def __init__(self, instructions: str = SYSTEM_PROMPT, user_role: str = "customer") -> None:
        super().__init__(instructions=instructions)
        self.user_role = user_role

    @function_tool
    async def lookup_caller(self, context: RunContext, user_id: str):
        """Look up a returning caller's saved info by their user ID.
        Call this early in the conversation once you have identified
        who you're speaking with, to check if they're a returning caller.

        Args:
            user_id: Caller identifier — phone number or normalized name
                     (lowercased, spaces replaced with underscores).
        """
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
        logger.info("Tool: get_shop_status called for shop_id=%s", shop_id)
        return services.get_shop_status(shop_id)

    @function_tool
    async def get_shop_info(self, context: RunContext):
        """Retrieve shop operating hours and physical store location/address."""
        import services
        logger.info("Tool: get_shop_info called")
        return services.get_shop_info()

    @function_tool
    async def lookup_product(self, context: RunContext, product_name: str):
        """Look up a product's price, unit size, and stock availability by name.

        Args:
            product_name: Name of the product or item to search for (e.g. 'milk', 'bread', 'rice').
        """
        import services
        logger.info("Tool: lookup_product called for product_name=%s", product_name)
        return services.lookup_product(product_name)

    @function_tool
    async def check_order_status(self, context: RunContext, query: str):
        """Check order status and delivery slot for an order ID or customer user ID.

        Args:
            query: Order ID (e.g. 'ord_001') or customer ID / phone number (e.g. 'user_rahul').
        """
        import services
        logger.info("Tool: check_order_status called for query=%s", query)
        return services.check_order_status(query)

    @function_tool
    async def log_sale(self, context: RunContext, item_name: str, quantity: float, unit: str, amount: float):
        """Log a completed sale into the sales ledger. OWNER ONLY.
        Always confirm parsed item name, quantity, unit, and total amount with the caller before calling this tool.

        Args:
            item_name: Name of the item sold (e.g. 'Rice', 'Milk').
            quantity: Quantity sold (e.g. 2, 0.5).
            unit: Unit of measurement (e.g. 'kg', 'packet', 'liter').
            amount: Total sale amount in Rupees (e.g. 120.0).
        """
        import services
        logger.info("Tool: log_sale called for item=%s, qty=%s, amount=%s", item_name, quantity, amount)
        return services.log_sale(item_name, quantity, unit, amount, user_role=self.user_role)

    @function_tool
    async def log_credit(self, context: RunContext, customer_name: str, amount: float, credit_type: str, note: str = ""):
        """Log a customer credit ('udhaar') entry — either credit given or repayment paid. OWNER ONLY.
        Always confirm customer name, amount, and whether it was given or paid with the caller before calling this tool.

        Args:
            customer_name: Customer's name (e.g. 'Ramesh', 'Rahul').
            amount: Credit amount in Rupees (e.g. 500.0).
            credit_type: 'given' (owner lent goods on credit) or 'paid' (customer paid back).
            note: Optional note (e.g. 'Groceries purchase', 'UPI payment').
        """
        import services
        logger.info("Tool: log_credit called for customer=%s, amt=%s, type=%s", customer_name, amount, credit_type)
        return services.log_credit(customer_name, amount, credit_type, note, user_role=self.user_role)

    @function_tool
    async def check_credit_balance(self, context: RunContext, customer_name: str):
        """Check current udhaar credit balance and transaction summary for a customer.

        Args:
            customer_name: Customer's name to query credit balance for.
        """
        import services
        logger.info("Tool: check_credit_balance called for customer=%s", customer_name)
        return services.check_credit_balance(customer_name)

    @function_tool
    async def leave_message_for_owner(self, context: RunContext, from_name: str, message_text: str):
        """Leave a message or note for the shop owner.
        Always confirm caller name and the message text with the caller before calling this tool.

        Args:
            from_name: Name of the caller leaving the message (defaults to 'Unknown' if not provided).
            message_text: The message content to deliver to the owner.
        """
        import services
        logger.info("Tool: leave_message_for_owner called from=%s", from_name)
        return services.leave_message_for_owner(from_name, message_text)

    @function_tool
    async def get_daily_summary(self, context: RunContext, date: str = ""):
        """Get daily sales aggregate summary including total revenue, transaction count, and top item.

        Args:
            date: Optional date string in YYYY-MM-DD format (defaults to today).
        """
        import services
        logger.info("Tool: get_daily_summary called for date=%s", date)
        return services.get_daily_summary(date)

    @function_tool
    async def get_market_price(self, context: RunContext, commodity: str, state: str = "", market: str = ""):
        """Fetch live commodity market price trends from Agmarknet API.

        Args:
            commodity: Name of agricultural commodity (e.g. 'Rice', 'Potato', 'Wheat', 'Onion').
            state: Optional Indian state name (e.g. 'Delhi', 'Punjab').
            market: Optional market center name.
        """
        import services
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
        logger.info(
            "Tool: create_escalation called for caller=%s, issue=%s, urgency=%s",
            caller_name, issue_type, urgency,
        )
        return services.create_escalation(
            caller_name=caller_name,
            issue_type=issue_type,
            summary=summary,
            urgency=urgency,
            language=language,
            contact_method=contact_method,
        )


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

    # Extract user role from participant metadata
    user_role = "customer"
    for participant in ctx.room.remote_participants.values():
        if participant.identity.startswith("voice_assistant_user_") and participant.metadata:
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
        user_role=user_label,
        role_objectives=role_obj
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

    # Start the session, which initializes the voice pipeline and warms up the models
    await session.start(
        agent=Assistant(instructions=formatted_instructions, user_role=user_role),
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

    try:
        await session.generate_reply(
            instructions=greet_inst
        )
    finally:
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

