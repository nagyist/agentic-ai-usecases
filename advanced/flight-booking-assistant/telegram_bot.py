import asyncio
import functools
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

from graph import booking_graph

load_dotenv()

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

INITIAL_STATE = {
    "messages": [],
    "last_user_input": "",
    "assistant_message": "",
    "step": "GREETING",
    "current_agent": "router",
    "intent": None,
    "process": "",
    "pnr": "",
    "departure_city": None,
    "destination_city": None,
    "travel_date": None,
    "return_date": None,
    "trip_type": None,
    "adults": None,
    "children": None,
    "confirmation_step": "",
    "flight_confirmed": None,
    "whatsapp_consent": None,
    "passenger_names": "",
    "passenger_error": "",
    "email": "",
    "flights": [],
    "selected_flight": {},
    "cities_updated": False,
    "slots_updated": False,
    "city_error": "",
    "slot_error": "",
    "awaiting_confirmation": False,
}

INITIAL_GREETING = (
    "Hello! I am 6ESkai, your friendly AI assistant from Indigo.\n"
    "How can I help you with our services today?\n\n"
    "- Book a flight ticket\n"
    "- Flight Status\n"
    "- Web Check-in"
)

# Per-user state keyed by Telegram chat_id
user_states: dict[int, dict] = {}


def _get_state(chat_id: int) -> dict:
    if chat_id not in user_states:
        user_states[chat_id] = dict(INITIAL_STATE)
        user_states[chat_id]["messages"] = []
        user_states[chat_id]["flights"] = []
        user_states[chat_id]["selected_flight"] = {}
    return user_states[chat_id]


async def _invoke_graph(chat_id: int, user_input: str, context: ContextTypes.DEFAULT_TYPE) -> str:
    state = _get_state(chat_id)
    state["last_user_input"] = user_input
    state["messages"].append({"role": "user", "content": user_input})

    async def keep_typing():
        while True:
            await context.bot.send_chat_action(chat_id=chat_id, action="typing")
            await asyncio.sleep(4)

    typing_task = asyncio.create_task(keep_typing())

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None, functools.partial(booking_graph.invoke, state)
        )
        user_states[chat_id] = result
        reply = result.get("assistant_message", "") or "I'm processing your request. Please try again."
        if result.get("assistant_message"):
            result["messages"].append({"role": "assistant", "content": reply})
    except Exception as e:
        print(f"[ERROR] chat_id={chat_id}: {e}")
        reply = "Sorry, something went wrong. Please try again or type /start to restart."
    finally:
        typing_task.cancel()

    return reply


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_states[chat_id] = dict(INITIAL_STATE)
    user_states[chat_id]["messages"] = []
    user_states[chat_id]["flights"] = []
    user_states[chat_id]["selected_flight"] = {}
    await update.message.reply_text(INITIAL_GREETING)


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    user_input = update.message.text.strip()
    reply = await _invoke_graph(chat_id, user_input, context)
    await update.message.reply_text(reply)


def main():
    if not BOT_TOKEN:
        raise ValueError("TELEGRAM_BOT_TOKEN is not set in .env")

    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    print(f"Bot @{os.getenv('TELEGRAM_BOT_USERNAME', 'unknown')} is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
