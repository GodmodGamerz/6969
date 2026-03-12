import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
import requests
from tavily import TavilyClient

logging.basicConfig(level=logging.INFO)

TELEGRAM_TOKEN = "8421541005:AAFLxKVTUi6Q3o_YHWga8EEVCWh5FKHGCP4"
NVIDIA_API_KEY = "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"
TAVILY_API_KEY = "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"

tavily = TavilyClient(api_key=TAVILY_API_KEY)

MODELS = {
    "kimi_k2":    {"id": "moonshotai/kimi-k2-instruct", "label": "Kimi K2 🌙"},
    "kimi_think": {"id": "moonshotai/kimi-k2-thinking", "label": "Kimi K2 Thinking 🧠"},
    "deepseek":   {"id": "deepseek-ai/deepseek-v3.2", "label": "DeepSeek V3.2 🔍"},
    "llama_4":    {"id": "meta/llama-4-maverick-17b-128e-instruct", "label": "Llama 4 Maverick 🦙"},
    "mistral":    {"id": "mistralai/mistral-large-2-instruct", "label": "Mistral Large ⚡"},
    "qwen3":      {"id": "qwen/qwen3.5-397b-a17b", "label": "Qwen 3.5 397B 🤖"},
    "gemma3":     {"id": "google/gemma-3-27b-it", "label": "Gemma 3 27B 🔷"},
    "phi4":       {"id": "microsoft/phi-4-mini-instruct", "label": "Phi-4 Mini 🔬"},
}

user_state = {}

def get_state(user_id):
    if user_id not in user_state:
        user_state[user_id] = {"model": "kimi_k2", "history": [], "web_search": True}
    return user_state[user_id]

def needs_search(message, model_id):
    try:
        headers = {
            "Authorization": f"Bearer {NVIDIA_API_KEY}",
            "Content-Type": "application/json"
        }
        data = {
            "model": model_id,
            "messages": [
                {
                    "role": "system",
                    "content": "You decide if a question needs a real-time web search to answer accurately. Reply with only YES or NO. Reply YES if the question is about current events, recent news, live data, prices, weather, sports scores, people's current roles, or anything that changes over time. Reply NO if it's a general knowledge, math, coding, or timeless question."
                },
                {
                    "role": "user",
                    "content": message
                }
            ],
            "max_tokens": 5,
            "temperature": 0,
        }
        response = requests.post(
            "https://integrate.api.nvidia.com/v1/chat/completions",
            headers=headers,
            json=data
        )
        answer = response.json()["choices"][0]["message"]["content"].strip().upper()
        return "YES" in answer
    except Exception as e:
        logging.error(f"Search decision error: {e}")
        return False

def search_web(query):
    try:
        results = tavily.search(query=query, max_results=3)
        snippets = []
        for r in results["results"]:
            snippets.append(f"- {r['title']}: {r['content'][:300]}")
        return "\n".join(snippets)
    except Exception as e:
        logging.error(f"Search error: {e}")
        return None

def ask_nvidia(model_id, messages):
    headers = {
        "Authorization": f"Bearer {NVIDIA_API_KEY}",
        "Content-Type": "application/json"
    }
    data = {
        "model": model_id,
        "messages": messages,
        "max_tokens": 1024,
        "temperature": 0.7,
    }
    response = requests.post(
        "https://integrate.api.nvidia.com/v1/chat/completions",
        headers=headers,
        json=data
    )
    return response.json()["choices"][0]["message"]["content"]

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 *Welcome to AI Chat Bot!*\n\n"
        "Powered by NVIDIA API + Real-time Web Search 🌐\n\n"
        "*Commands:*\n"
        "• /model — Switch AI model\n"
        "• /reset — Clear chat history\n"
        "• /current — Show current model\n"
        "• /search — Toggle web search on/off\n\n"
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
    search_status = "🟢 On" if state["web_search"] else "🔴 Off"
    await update.message.reply_text(
        f"🤖 Current model: *{model['label']}*\n"
        f"`{model['id']}`\n\n"
        f"🌐 Web Search: {search_status}",
        parse_mode="Markdown"
    )

async def toggle_search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    state = get_state(update.effective_user.id)
    state["web_search"] = not state["web_search"]
    status = "🟢 ON" if state["web_search"] else "🔴 OFF"
    await update.message.reply_text(
        f"🌐 Web search is now *{status}*",
        parse_mode="Markdown"
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    state = get_state(user_id)
    user_message = update.message.text
    state["history"].append({"role": "user", "content": user_message})
    await context.bot.send_chat_action(chat_id=update.effective_chat.id, action="typing")

    try:
        system_prompt = "You are a helpful, smart, and friendly AI assistant."

        if state["web_search"] and needs_search(user_message, MODELS[state["model"]]["id"]):
            await update.message.reply_text("🔍 Searching the web...")
            search_results = search_web(user_message)
            if search_results:
                system_prompt += (
                    f"\n\nHere is real-time web search data to help answer the user's question:\n"
                    f"{search_results}\n\n"
                    f"Use this information to give an up-to-date accurate answer."
                )

        messages = [
            {"role": "system", "content": system_prompt},
            *state["history"],
        ]

        reply = ask_nvidia(MODELS[state["model"]]["id"], messages)
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
    app.add_handler(CommandHandler("search", toggle_search))
    app.add_handler(CallbackQueryHandler(model_callback, pattern="^model:"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    print("✅ Bot is running!")
    app.run_polling()

if __name__ == "__main__":
    main()
