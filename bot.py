import asyncio
import logging
import sqlite3
import os
from datetime import datetime
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext
from google_sheets import init_google_sheets

# Токен бота
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
    logger.info("✅ База данных SQLite инициализирована")

# Инициализируем Google Sheets при старте
from google_sheets import gs_manager

# Команда /start
def start(update: Update, context: CallbackContext):
    text = (
        "📊 Бот для учета счетов\n\n"
        "Я помогу вам:\n"
        "• Добавлять счета\n"
        "• Вести учет\n"
        "• Управлять поставщиками\n"
        "• Сохранять в Google Таблицу\n\n"
        "Доступные команды:\n"
        "/add - Добавить новый счет\n"
        "/list - Показать мои счета\n"
        "/help - Помощь\n\n"
        "Бот работает 24/7 на Render!"
    )
    update.message.reply_text(text)

# Команда /add
def add_invoice(update: Update, context: CallbackContext):
    text = (
        "📝 Добавление счета\n\n"
        "Отправьте данные в формате:\n"
        "Номер_счета Дата Поставщик Сумма [Назначение]\n\n"
        "Пример:\n"
        "INV-2024-001 15.01.2024 ТОО_Ромашка 50000 Оборудование\n\n"
        "Для срочного счета добавьте ! в конце:\n"
        "СЧ-001 20.01.2024 ИП_Иванов 25000 Услуги !"
    )
    update.message.reply_text(text)

# Команда /list
def list_invoices(update: Update, context: CallbackContext):
    try:
        conn = sqlite3.connect('invoices.db')
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, invoice_number, invoice_date, supplier, amount, purpose, priority, created_at
            FROM invoices 
            ORDER BY created_at DESC 
            LIMIT 10
        ''')
        invoices = cursor.fetchall()
        conn.close()
        
        if not invoices:
            update.message.reply_text("📭 Счетов пока нет\n\nДобавьте первый счет командой /add")
            return
        
        response = "📋 Последние счета:\n\n"
        for inv in invoices:
            priority_icon = "🚀" if inv[6] == 'urgent' else "⏳"
            response += (
                f"{priority_icon} #{inv[0]} {inv[1]}\n"
                f"📅 {inv[2]} | 🏢 {inv[3]}\n"
                f"💰 {inv[4]:,.2f} ₸\n"
                f"📝 {inv[5] or 'Не указано'}\n"
                f"🕒 {inv[7][:16]}\n"
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
        
        update.message.reply_text(response)
        
    except Exception as e:
        logger.error(f"Ошибка в /list: {e}")
        update.message.reply_text("❌ Ошибка при получении счетов")

# Команда /help
def help_command(update: Update, context: CallbackContext):
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
    update.message.reply_text(text)

# Обработка текстовых сообщений
def handle_text(update: Update, context: CallbackContext):
    text = update.message.text.strip()
    
    # Если сообщение похоже на счет
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
            
            # Сохраняем в SQLite
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
            
            # Сохраняем в Google Sheets
            gs_success = False
            if gs_manager:
                invoice_data = {
                    'number': invoice_number,
                    'date': invoice_date,
                    'supplier': supplier,
                    'amount': amount,
                    'purpose': purpose,
                    'priority': priority
                }
                gs_success = gs_manager.add_invoice(invoice_data)
            
            # Формируем ответ
            priority_text = "🚀 СРОЧНЫЙ" if priority == 'urgent' else "⏳ Обычный"
            
            response = (
                f"✅ Счет #{invoice_id} добавлен!\n\n"
                f"📋 Номер: {invoice_number}\n"
                f"📅 Дата: {invoice_date}\n"
                f"🏢 Поставщик: {supplier}\n"
                f"💰 Сумма: {amount:,.2f} ₸\n"
                f"📝 Назначение: {purpose or 'Не указано'}\n"
                f"🎯 Приоритет: {priority_text}\n"
            )
            
            if gs_success:
                response += f"\n📊 Данные сохранены в Google Таблицу!"
            else:
                response += f"\n📝 Данные сохранены локально"
            
            response += f"\n\nДля просмотра всех счетов: /list"
            
            update.message.reply_text(response)
            
        except ValueError:
            update.message.reply_text(
                "❌ Ошибка формата!\n\n"
                "Правильный формат:\n"
                "Номер Дата Поставщик Сумма [Назначение] [!]\n\n"
                "Пример:\n"
                "INV-001 15.01.2024 Поставщик 50000 Оборудование"
            )
        except Exception as e:
            logger.error(f"Ошибка добавления счета: {e}")
            update.message.reply_text(f"❌ Ошибка: {str(e)}")
    
    # Простые ответы
    elif 'привет' in text.lower():
        update.message.reply_text("Привет! 👋 Для работы со счетами используйте /add")
    elif 'спасибо' in text.lower():
        update.message.reply_text("Всегда рад помочь! 😊")
    elif 'бот' in text.lower():
        update.message.reply_text("Я здесь! Чем могу помочь?")
    else:
        update.message.reply_text(
            "Используйте команды:\n"
            "/start - начало работы\n"
            "/add - добавить счет\n" 
            "/list - список счетов\n"
            "/help - помощь"
        )

# Главная функция
def main():
    # Инициализируем базу данных
    init_db()
    
    # Инициализируем Google Sheets
    if init_google_sheets():
        logger.info("✅ Google Sheets интеграция включена")
    else:
        logger.info("⚠️ Google Sheets интеграция отключена")
    
    # Создаем Updater
    updater = Updater(TOKEN, use_context=True)
    dispatcher = updater.dispatcher
    
    # Добавляем обработчики
    dispatcher.add_handler(CommandHandler("start", start))
    dispatcher.add_handler(CommandHandler("add", add_invoice))
    dispatcher.add_handler(CommandHandler("list", list_invoices))
    dispatcher.add_handler(CommandHandler("help", help_command))
    dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_text))
    
    # Запускаем бота
    logger.info("=== БОТ ДЛЯ СЧЕТОВ ЗАПУЩЕН ===")
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
