import asyncio
import logging
import sqlite3
from datetime import datetime
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes

# ТВОЙ ТОКЕН
TOKEN = "8397642444:AAHE9_BqSh8IPuqe5Ojmcyj-Q89okIHhykU"

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Инициализация базы данных
def init_db():
    conn = sqlite3.connect('invoices.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS invoices (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            invoice_number TEXT NOT NULL,
            invoice_date TEXT,
            supplier TEXT,
            amount REAL,
            purpose TEXT,
            priority TEXT DEFAULT 'normal',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()
    conn.close()
    logger.info("База данных инициализирована")

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📊 Бот для учета счетов\n\n"
        "Я помогу вам:\n"
        "• Добавлять счета\n"
        "• Вести учет\n"
        "• Управлять поставщиками\n\n"
        "Доступные команды:\n"
        "/add - Добавить новый счет\n"
        "/list - Показать мои счета\n"
        "/help - Помощь\n\n"
        "Бот работает 24/7 на Render!"
    )
    await update.message.reply_text(text)

# Команда /add - показать инструкцию
async def add_invoice(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "📝 Добавление счета\n\n"
        "Отправьте данные в формате:\n"
        "Номер_счета Дата Поставщик Сумма [Назначение]\n\n"
        "Пример:\n"
        "INV-2024-001 15.01.2024 ТОО_Ромашка 50000 Оборудование\n\n"
        "Для срочного счета добавьте ! в конце:\n"
        "СЧ-001 20.01.2024 ИП_Иванов 25000 Услуги !"
    )
    await update.message.reply_text(text)

# Команда /list - показать счета
async def list_invoices(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        conn = sqlite3.connect('invoices.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, invoice_number, invoice_date, supplier, amount, priority, created_at
            FROM invoices 
            ORDER BY created_at DESC 
            LIMIT 10
        ''')
        invoices = cursor.fetchall()
        conn.close()
        
        if not invoices:
            await update.message.reply_text("📭 Счетов пока нет\n\nДобавьте первый счет командой /add")
            return
        
        response = "📋 Последние счета:\n\n"
        for inv in invoices:
            priority_icon = "🚀" if inv[5] == 'urgent' else "⏳"
            response += (
                f"{priority_icon} #{inv[0]} {inv[1]}\n"
                f"📅 {inv[2]} | 🏢 {inv[3]}\n"
                f"💰 {inv[4]:,.2f} ₸\n"
                f"🕒 {inv[6][:16]}\n"
                f"────────────────────\n"
            )
        
        # Статистика
        conn = sqlite3.connect('invoices.db')
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*), SUM(amount) FROM invoices")
        stats = cursor.fetchone()
        conn.close()
        
        response += (
            f"\n📊 Статистика:\n"
            f"• Всего счетов: {stats[0] or 0}\n"
            f"• Общая сумма: {(stats[1] or 0):,.2f} ₸\n\n"
            f"Добавить новый: /add"
        )
        
        await update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Ошибка в /list: {e}")
        await update.message.reply_text("❌ Ошибка при получении счетов")

# Команда /help
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (
        "🆘 Помощь по боту\n\n"
        "Как добавить счет:\n"
        "1. Напишите /add\n"
        "2. Отправьте данные в формате:\n"
        "   Номер Дата Поставщик Сумма Назначение\n\n"
        "Примеры:\n"
        "• INV-001 15.01.2024 ТОО_Ромашка 50000 Оборудование\n"
        "• СЧ-2024-001 20.01.2024 ИП_Иванов 25000 !\n\n"
        "Команды:\n"
        "/start - Начало работы\n"
        "/add - Добавить счет\n"
        "/list - Список счетов\n"
        "/help - Эта справка"
    )
    await update.message.reply_text(text)

# Обработка текстовых сообщений (добавление счетов)
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    # Если сообщение похоже на счет (содержит цифры и не команда)
    if (len(text.split()) >= 3 and 
        not text.startswith('/') and
        any(char.isdigit() for char in text)):
        
        try:
            parts = text.split()
            
            # Определяем приоритет
            if parts[-1] == '!':
                priority = 'urgent'
                parts = parts[:-1]  # Убираем !
            else:
                priority = 'normal'
            
            # Парсим данные
            invoice_number = parts[0]
            invoice_date = parts[1]
            supplier = parts[2]
            amount = float(parts[3].replace(',', '.'))
            purpose = ' '.join(parts[4:]) if len(parts) > 4 else ''
            
            # Сохраняем в базу
            conn = sqlite3.connect('invoices.db')
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO invoices 
                (invoice_number, invoice_date, supplier, amount, purpose, priority)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (invoice_number, invoice_date, supplier, amount, purpose, priority))
            conn.commit()
            invoice_id = cursor.lastrowid
            conn.close()
            
            # Формируем ответ
            priority_text = "🚀 СРОЧНЫЙ" if priority == 'urgent' else "⏳ Обычный"
            
            response = (
                f"✅ Счет #{invoice_id} добавлен!\n\n"
                f"📋 Номер: {invoice_number}\n"
                f"📅 Дата: {invoice_date}\n"
                f"🏢 Поставщик: {supplier}\n"
                f"💰 Сумма: {amount:,.2f} ₸\n"
                f"📝 Назначение: {purpose or 'Не указано'}\n"
                f"🎯 Приоритет: {priority_text}\n\n"
                f"Для просмотра всех счетов: /list"
            )
            await update.message.reply_text(response)
            
        except ValueError:
            await update.message.reply_text(
                "❌ Ошибка формата!\n\n"
                "Правильный формат:\n"
                "Номер Дата Поставщик Сумма [Назначение] [!]\n\n"
                "Пример:\n"
                "INV-001 15.01.2024 Поставщик 50000 Оборудование"
            )
        except Exception as e:
            logger.error(f"Ошибка добавления счета: {e}")
            await update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    # Простые ответы
    elif 'привет' in text.lower():
        await update.message.reply_text("Привет! 👋 Для работы со счетами используйте /add")
    elif 'спасибо' in text.lower():
        await update.message.reply_text("Всегда рад помочь! 😊")
    elif 'бот' in text.lower():
        await update.message.reply_text("Я здесь! Чем могу помочь?")
    else:
        # Если не распознано как счет
        await update.message.reply_text(
            "Используйте команды:\n"
            "/start - начало работы\n"
            "/add - добавить счет\n" 
            "/list - список счетов\n"
            "/help - помощь"
        )

# Главная функция
async def main():
    # Инициализируем базу данных
    init_db()
    
    # Создаем Application
    application = Application.builder().token(TOKEN).build()
    
    # Добавляем обработчики команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("add", add_invoice))
    application.add_handler(CommandHandler("list", list_invoices))
    application.add_handler(CommandHandler("help", help_command))
    
    # Добавляем обработчик текстовых сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # Запускаем бота
    logger.info("=== БОТ ДЛЯ СЧЕТОВ ЗАПУЩЕН ===")
    await application.initialize()
    await application.start()
    await application.updater.start_polling()
    
    # Бесконечное ожидание
    await asyncio.Event().wait()

# Точка входа
if __name__ == "__main__":
    asyncio.run(main())
