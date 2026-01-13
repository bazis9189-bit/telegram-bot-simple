import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# ТВОЙ ТОКЕН (замени на свой!)
TOKEN = "8397642444:AAHE9_BqSh8IPuqe5Ojmcyj-Q89okIHhykU"

logging.basicConfig(level=logging.INFO)

async def start(update: Update, context):
    await update.message.reply_text("✅ БОТ ЗАПУЩЕН И РАБОТАЕТ!")

async def echo(update: Update, context):
    await update.message.reply_text(f"Вы написали: {update.message.text}")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    print("=== БОТ СТАРТУЕТ ===")
    app.run_polling()

if __name__ == "__main__":
    main()
