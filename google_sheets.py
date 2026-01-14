import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import logging
import os
import json

logger = logging.getLogger(__name__)

class GoogleSheetsManager:
    def __init__(self):
        try:
            # ID твоей таблицы (замени если нужно)
            self.spreadsheet_id = "1ZycCYoIVq1QDMaABP1whJhYIP3B8_O0wX1xH0W3sGtU"
            
            logger.info("🔄 Пытаюсь подключиться к Google Sheets...")
            
            # Получаем credentials из переменной окружения
            creds_json = os.getenv('GOOGLE_CREDENTIALS_JSON')
            
            if not creds_json:
                logger.warning("⚠️ GOOGLE_CREDENTIALS_JSON не найден")
                logger.info("ℹ️ Проверь что на Render добавлена переменная GOOGLE_CREDENTIALS_JSON")
                return
            
            logger.info("✅ GOOGLE_CREDENTIALS_JSON найден")
            
            # Преобразуем строку JSON в словарь
            try:
                creds_data = json.loads(creds_json)
                logger.info("✅ JSON успешно распарсен")
            except json.JSONDecodeError as e:
                logger.error(f"❌ Ошибка парсинга JSON: {e}")
                return
            
            # Авторизация
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            try:
                creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_data, scope)
                client = gspread.authorize(creds)
                logger.info("✅ Авторизация в Google пройдена")
            except Exception as e:
                logger.error(f"❌ Ошибка авторизации: {e}")
                return
            
            # Открываем таблицу
            try:
                self.spreadsheet = client.open_by_key(self.spreadsheet_id)
                logger.info(f"✅ Таблица найдена: {self.spreadsheet.title}")
            except Exception as e:
                logger.error(f"❌ Не могу открыть таблицу с ID {self.spreadsheet_id}: {e}")
                logger.info("ℹ️ Проверь: 1) ID таблицы, 2) Доступ сервисного аккаунта")
                return
            
            # Получаем или создаем лист "Счета"
            try:
                self.sheet = self.spreadsheet.worksheet('Счета')
                logger.info("✅ Лист 'Счета' найден")
            except:
                logger.info("📝 Создаю лист 'Счета'...")
                try:
                    self.sheet = self.spreadsheet.add_worksheet(title='Счета', rows=1000, cols=10)
                    # Заголовки
                    headers = ['ID', 'Номер счета', 'Дата', 'Поставщик', 'Сумма', 'Назначение', 'Приоритет', 'Время добавления']
                    self.sheet.append_row(headers)
                    logger.info("✅ Лист 'Счета' создан с заголовками")
                except Exception as e:
                    logger.error(f"❌ Ошибка создания листа: {e}")
                    return
            
            logger.info(f"🎉 Google Sheets подключен успешно!")
            
        except Exception as e:
            logger.error(f"❌ Критическая ошибка в GoogleSheetsManager: {e}")
            raise
    
    def add_invoice(self, invoice_data):
        """Добавить счет в таблицу"""
        try:
            # Получаем все строки для определения ID
            all_rows = self.sheet.get_all_values()
            new_id = len(all_rows)  # Первая строка - заголовки
            
            # Подготавливаем строку
            new_row = [
                new_id,  # ID
                invoice_data.get('number', ''),
                invoice_data.get('date', ''),
                invoice_data.get('supplier', ''),
                invoice_data.get('amount', 0),
                invoice_data.get('purpose', ''),
                '🚀 Срочный' if invoice_data.get('priority') == 'urgent' else '⏳ Обычный',
                datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            ]
            
            # Добавляем строку в таблицу
            self.sheet.append_row(new_row)
            logger.info(f"✅ Счет добавлен в Google Sheets: {invoice_data.get('number')}")
            return True
            
        except Exception as e:
            logger.error(f"❌ Ошибка записи в Google Sheets: {e}")
            return False

# Глобальный экземпляр
gs_manager = None

def init_google_sheets():
    """Инициализация Google Sheets"""
    global gs_manager
    try:
        gs_manager = GoogleSheetsManager()
        if gs_manager:
            logger.info("✅ Google Sheets менеджер инициализирован")
            return True
        else:
            logger.warning("⚠️ Google Sheets менеджер не создан")
            return False
    except Exception as e:
        logger.warning(f"⚠️ Google Sheets отключен: {e}")
        return False
