import asyncio
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters

# ТВОЙ ТОКЕН
TOKEN = "8397642444:AAHE9_BqSh8IPuqe5Ojmcyj-Q89okIHhykU"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context):
    await update.message.reply_text("✅ БОТ ЗАПУЩЕН И РАБОТАЕТ!")

async def echo(update: Update, context):
    await update.message.reply_text(f"Вы: {update.message.text}")

async def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echo))
    
    logger.info("=== БОТ ЗАПУЩЕН ===")
    await app.initialize()
    await app.start()
    await app.updater.start_polling()
    
    # Бесконечное ожидание
    await asyncio.Event().wait()

if __name__ == "__main__":
    asyncio.run(main())
