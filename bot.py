import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# ТВОЙ ТОКЕН
TOKEN = "8397642444:AAHE9_BqSh8IPuqe5Ojmcyj-Q89okIHhykU"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def start(update, context):
    update.message.reply_text("✅ БОТ ЗАПУЩЕН И РАБОТАЕТ!")

def echo(update, context):
    update.message.reply_text(f"Вы написали: {update.message.text}")

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher
    
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))
    
    logger.info("=== БОТ СТАРТУЕТ ===")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
