import telebot
import requests
import time
from telebot import types

# --- CONFIGURATION ---
API_TOKEN = '8266344816:AAHboT_wENRpa_i3Vlet_SqNcYnDvAFKAs0'
bot = telebot.TeleBot(API_TOKEN, parse_mode="Markdown")

# Global storage (In production, use a Database or JSON file)
user_sessions = {} 

# --- HELPER FUNCTIONS ---
def validate_maytapi(url):
    """
    Validates the Maytapi URL/Token by hitting the status endpoint.
    Expected URL format: https://api.maytapi.com/api/<product_id>/<phone_id>
    """
    try:
        # Example check to see if the instance is logged in
        response = requests.get(f"{url}/status")
        if response.status_code == 200:
            return True
        return False
    except:
        return False

def create_main_markup():
    markup = types.InlineKeyboardMarkup(row_width=2)
    btn1 = types.InlineKeyboardButton("🔍 CHECK API", callback_data="check_api")
    btn2 = types.InlineKeyboardButton("📲 WSTP CHECKER", callback_data="start_checker")
    markup.add(btn1, btn2)
    return markup

# --- BOT HANDLERS ---

@bot.message_handler(commands=['start', 'restart'])
def send_welcome(message):
    chat_id = message.chat.id
    welcome_text = (
        "👋 *Welcome to WstpVerify Bot!*\n\n"
        "🤖 I am your advanced WhatsApp Status Checker.\n"
        "⚡ I can validate bulk numbers in seconds!\n\n"
        "💥 *Created By:* @Lohit_69"
    )
    bot.send_message(chat_id, welcome_text, reply_markup=create_main_markup())

@bot.callback_query_handler(func=lambda call: True)
def handle_query(call):
    chat_id = call.message.chat.id
    
    if call.data == "check_api":
        if chat_id in user_sessions and 'api_url' in user_sessions[chat_id]:
            url = user_sessions[chat_id]['api_url']
            if validate_maytapi(url):
                msg = f"✅ *Maytapi Api is Connected*\n🟢 Status: Active\n🔗 URL: `{url}`"
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton("🗑 Remove API", callback_data="remove_api"))
                bot.edit_message_text(msg, chat_id, call.message.message_id, reply_markup=markup)
            else:
                bot.send_message(chat_id, "⚠️ *API Disconnected!* Please update your URL.")
                ask_for_api(chat_id)
        else:
            bot.send_message(chat_id, "❌ *Maytapi Api not connected* 🔴")
            ask_for_api(chat_id)

    elif call.data == "remove_api":
        user_sessions.pop(chat_id, None)
        bot.answer_callback_query(call.id, "API Removed successfully!")
        send_welcome(call.message)

    elif call.data == "start_checker":
        if chat_id not in user_sessions or 'api_url' not in user_sessions[chat_id]:
            bot.send_message(chat_id, "🚫 *Connect API first!*")
            ask_for_api(chat_id)
        else:
            bot.send_message(chat_id, "📥 *Send WhatsApp numbers to check.*\n(One per line or comma-separated. With or without +)")

def ask_for_api(chat_id):
    msg = bot.send_message(chat_id, "⌨️ Please send your *Maytapi API URL*:")
    bot.register_next_step_handler(msg, save_api)

def save_api(message):
    url = message.text.strip()
    bot.send_message(message.chat.id, "⏳ *Verifying connection...*")
    
    if validate_maytapi(url):
        user_sessions[message.chat.id] = {'api_url': url}
        bot.send_message(message.chat.id, "✅ *Maytapi Api is Connected* 🟢", reply_markup=create_main_markup())
    else:
        bot.send_message(message.chat.id, "❌ *Connection Failed!* Check your URL/Token and try again.")
        ask_for_api(message.chat.id)

@bot.message_handler(func=lambda message: True)
def handle_numbers(message):
    chat_id = message.chat.id
    if chat_id not in user_sessions: return

    # Clean the input numbers
    raw_numbers = message.text.replace(',', '\n').split('\n')
    numbers = [n.strip().replace('+', '') for n in raw_numbers if n.strip()]
    
    if not numbers: return

    total = len(numbers)
    progress_msg = bot.send_message(chat_id, f"🌀 *Processing:* 0/{total}\n[░░░░░░░░░░] 0%")
    
    results = []
    registered = 0
    banned = 0
    fresh = 0

    for i, num in enumerate(numbers):
        # API logic to Maytapi (Simplified)
        try:
            # Note: Maytapi usually requires 'number' in international format without '+'
            res = requests.get(f"{user_sessions[chat_id]['api_url']}/checkNumberStatus", params={"number": num})
            data = res.json()
            
            # This logic depends on the specific Maytapi response structure
            if data.get('status') == 'banned':
                results.append(f"`{num}` ⛔️")
                banned += 1
            elif data.get('registered') == True:
                results.append(f"`{num}` 🔐")
                registered += 1
            else:
                results.append(f"`{num}` ✅")
                fresh += 1
        except:
            results.append(f"`{num}` ⚠️ (Error)")

        # Update Progress Bar
        percent = int(((i + 1) / total) * 100)
        bar_len = 10
        filled = int(percent / 10)
        bar = "█" * filled + "░" * (bar_len - filled)
        
        if (i + 1) % 2 == 0 or (i + 1) == total: # Update every 2 for performance
            bot.edit_message_text(f"🌀 *Processing:* {i+1}/{total}\n[{bar}] {percent}%", chat_id, progress_msg.message_id)

    # Final Result
    final_text = (
        f"📊 *Checking Complete!*\n\n"
        f"✅ Fresh: {fresh}\n"
        f"🔐 Registered: {registered}\n"
        f"⛔️ Banned: {banned}\n\n"
        "📝 *Results (Click to copy):*\n" + "\n".join(results)
    )
    bot.send_message(chat_id, final_text, reply_markup=create_main_markup())

bot.infinity_polling()