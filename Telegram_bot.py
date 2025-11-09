import requests
import json
import logging
import os # 'os' library environment variables के लिए ज़रूरी है
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# === CONFIGURATION: Environment Variables का उपयोग करें ===
# Pella.app पर सुरक्षित रूप से सेट करने के लिए:
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
API_TOKEN = os.environ.get("EXTERNAL_API_TOKEN", "7576981793:2WnIfAmi")
LANG = os.environ.get("LANG", "ru")
LIMIT = int(os.environ.get("LIMIT", 300))
URL = os.environ.get("API_URL", "https://leakosintapi.com/")

# Webhook configuration
PORT = int(os.environ.get("PORT", 8080)) # Pella द्वारा प्रदान किया गया पोर्ट
WEBHOOK_URL = os.environ.get("WEBHOOK_URL") # Pella द्वारा प्रदान किया गया सार्वजनिक URL

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# === Utility Functions (Data Formatter and API Caller) ===

def format_as_js(data):
    """Formats the JSON entry into a readable <pre> block for Telegram."""
    js_lines = []
    for key, value in data.items():
        value_str = json.dumps(value, ensure_ascii=False)
        js_lines.append(f"  {key}: {value_str}")
    
    return "\n".join(js_lines)

def generate_report(query: str) -> str:
    """External API को कॉल करता है और परिणाम को HTML-formatted string में लौटाता है।"""
    data = {
        "token": API_TOKEN,
        "request": query.strip(),
        "limit": LIMIT,
        "lang": LANG
    }
    
    MAX_RESPONSE_LEN = 3500 
    response_text = ""

    # API call logic (same as before)
    try:
        response = requests.post(URL, json=data, timeout=10).json()
    except requests.exceptions.Timeout:
        return "❌ API Error: Request timed out. The external service took too long to respond."
    except requests.RequestException as e:
        return f"❌ API Error: A network error occurred: {e}"
    except json.JSONDecodeError:
        return "❌ API Error: Received an unreadable response from the external service."
    
    if "Error code" in response:
        return f"🚫 <b>API Error:</b> <code>{response['Error code']}</code>"
    
    if not response.get("List"):
        return "⚠️ No data found in the response."

    results_found = False
    
    for db, db_content in response["List"].items():
        if not db_content or db == "No results found":
            continue

        results_found = True
        
        db_title = "Professor Anish" if db.lower() == "1win" else db
        response_text += f"\n\n<b>=== [ DATABASE: {db_title} ] ===</b>\n"

        if db_content.get("Data"):
            for entry in db_content["Data"]:
                formatted_entry = format_as_js(entry)
                response_text += f"<pre>\n{formatted_entry}\n</pre>"
                
                if len(response_text) > MAX_RESPONSE_LEN:
                    response_text += "\n... results truncated due to Telegram message length limit."
                    break
        
        if len(response_text) > MAX_RESPONSE_LEN:
            break
            
    if not results_found:
        return "🔍 Search complete. No results found for your query."

    return response_text

# === Telegram Handler Functions ===

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command."""
    welcome_message = (
        "👑 **Welcome to the Report Generator Bot!** 👑\n\n"
        "This bot is powered by <b>R☉LEX SIR IO ⚜️</b>\n\n"
        "❓ **How to use:**\n"
        "Just send me the <b>Target Query</b> (phone number, email, or username) you want to search for.\n\n"
        "I will quickly generate the external API report for you."
    )
    await update.message.reply_html(welcome_message)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the user's text message and runs the report."""
    query = update.message.text
    
    if len(query) < 4:
        await update.message.reply_text("Please provide a valid query (e.g., phone number or email) to search.")
        return
        
    await update.message.reply_text(f"🔍 Searching for <b>{query}</b>... This may take a moment.", parse_mode='HTML')
    
    report = generate_report(query)
    
    await update.message.reply_html(report)

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.warning('Update "%s" caused error "%s"', update, context.error)
    if update.effective_message:
        await update.effective_message.reply_text(
            "An internal error occurred while processing your request. Please try again later."
        )

def main() -> None:
    """Start the bot using Webhook mode for cloud deployment."""
    if not TELEGRAM_BOT_TOKEN or not WEBHOOK_URL:
        logger.error("!!! FATAL ERROR: TELEGRAM_BOT_TOKEN or WEBHOOK_URL is missing. Set them in Pella.app Environment Variables.")
        print("!!! FATAL ERROR: TELEGRAM_BOT_TOKEN or WEBHOOK_URL is missing. Set them in Pella.app Environment Variables.")
        return
        
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_error_handler(error_handler)

    # Webhook mode में run करना
    print(f"Starting Webhook on port {PORT} with URL {WEBHOOK_URL}...")
    
    application.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TELEGRAM_BOT_TOKEN, 
        webhook_url=f"{WEBHOOK_URL}/{TELEGRAM_BOT_TOKEN}"
    )

if __name__ == '__main__':
    main()

