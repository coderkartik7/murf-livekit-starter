import logging

from dotenv import load_dotenv
from livekit import rtc
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

STYLE
Keep replies to one or two short sentences — this is spoken audio, not a chat window. No lists, no bullet points, no brackets, no sentence over about 20 words. Always confirm what you understood before treating an update as final. If the user goes quiet, gently check in rather than staying silent.
"""

OWNER_OBJECTIVES = """1. A vendor/owner logs a sale or stock update, and you confirm it back accurately before treating it as done.
2. If they ask for business-related details (like shop hours, logged udhaar, summaries), help them query it or update it.
3. Be friendly, brief, and highly functional for shop operations."""

CUSTOMER_OBJECTIVES = """1. A customer gets an accurate answer about product availability, price, or shop hours — or is told honestly that you don't know and the owner will follow up.
2. Any request outside what the owner has explicitly told you (discounts, delivery promises, order confirmations) is politely deferred, never guessed.
3. Let them leave a message if they want to get in touch with the shop owner."""


class Assistant(Agent):
    def __init__(self, instructions: str = SYSTEM_PROMPT) -> None:
        super().__init__(instructions=instructions)

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
        facts: dict,
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
            facts: Dict of learned facts — e.g. past_orders,
                   usual_quantities, preferred_delivery_slot.
        """
        logger.info("Saving caller info for: %s", user_id)
        await db.upsert_caller(user_id, name, role, language_preference, facts)
        return {"status": "saved", "user_id": user_id}


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

    # Format objectives based on role
    if user_role == "owner":
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
        agent=Assistant(instructions=formatted_instructions),
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

    await session.generate_reply(
        instructions=greet_inst
    )


if __name__ == "__main__":
    cli.run_app(server)

