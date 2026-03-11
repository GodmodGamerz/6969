import logging
from openai import OpenAI
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = "8421541005:AAFLxKVTUi6Q3o_YHWga8EEVCWh5FKHGCP4"
NVIDIA_API_KEY = "TAgTmK392MiBA07boooTmQgO6LL8kwcUMN35ffuoh_qIIDBH1RdlA"

client = OpenAI(
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=NVIDIA_API_KEY,
)

MODELS = {
    "kimi_k2": {"id": "moonshotai/kimi-k2", "label": "Kimi K2 🌙"},
    "llama_4":  {"id": "meta/llama-4-maverick-17b-128e-instruct", "label": "Llama 4 🦙"},
    "deepseek": {"id": "deepseek-ai/deepseek-r1", "label": "DeepSeek R1 🔍"},
    "mistral":  {"id": "mistralai/mistral-large-2-instruct", "label": "Mistral Large ⚡"},
    "qwen3":    {"id": "qwen/qwen3-235b-a22b", "label": "Qwen3 235B 🧠"},
}

user_state = {}

def get_state(user_id):
    if user_id not in user_state:
        user_state[user_id] = {"model": "kimi_k2", "history": []}
    return user_state[user_id]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Welcome to AI Chat Bot!*\n\n"
        "Powered by NVIDIA API with multiple AI models.\n\n"
        "*Commands:*\n"
        "• /model — Switch AI model\n"
        "• /reset — Clear chat history\n"
        "• /current — Show current model\n\n"
        "Start chatting! 🚀",
        parse_mode="Markdown"
    )

async def model_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = get_state(update.effective_user.id)
    keyboard = []
    for key, model in MODELS.items():
        is_active = "✅ " if state["model"] == key else ""
        keyboard.append([InlineKeyboardButton(
            f"{is_active}{model['label']}", callback_data=f"model:{key}"
        )])
    await update.message.reply_text(
        "🤖 *Choose your AI model:*",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def model_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    key = query.data.split(":")[1]
    state = get_state(query.from_user.id)
    if key not in MODELS:
        return
    state["model"] = key
    state["history"] = []
    await query.edit_message_text(
        f"✅ Switched to *{MODELS[key]['label']}*\n\nChat history cleared!",
        parse_mode="Markdown"
    )

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE):
    get_state(update.effective_user.id)["history"] = []
    await update.message.reply_text("🔄 Chat history cleared! Start fresh.")

async def current(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = get_state(update.effective_user.id)
    model = MODELS[state["model"]]
    await update.message.reply_text(
        f"🤖 Current model: *{model['label']}*\n`{model['id']}`",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = get_state(user_id)
    user_message = update.message.text
    state["history"].append({"role": "user", "content": user_message})
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")
    try:
        response = client.chat.completions.create(
            model=MODELS[state["model"]]["id"],
            messages=[
                {"role": "system", "content": "You are a helpful, smart, and friendly AI assistant."},
                *state["history"],
            ],
            max_tokens=1024,
            temperature=0.7,
        )
        reply = response.choices[0].message.content
        state["history"].append({"role": "assistant", "content": reply})
        if len(state["history"]) > 20:
            state["history"] = state["history"][-20:]
        await update.message.reply_text(reply)
    except Exception as e:
        logging.error(e)
        await update.message.reply_text("❌ Error getting response. Try /model to switch models.")

def main():
    app = Application.builder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("model", model_command))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(CommandHandler("current", current))
    app.add_handler(CallbackQueryHandler(model_callback, pattern="^model:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot is running!")
    app.run_polling()

if __name__ == "__main__":
    main()
