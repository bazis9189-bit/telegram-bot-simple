import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import logging
import os

logger = logging.getLogger(__name__)

class GoogleSheetsManager:
    def __init__(self):
        try:
            # ID твоей таблицы
            self.spreadsheet_id = "1ZycCYoIVq1QDMaABP1whJhYIP3B8_O0wX1xH0W3sGtU"
            
            # Проверяем файл credentials
            if not os.path.exists('credentials.json'):
                logger.warning("❌ Файл credentials.json не найден!")
                return
            
            # Авторизация
            scope = [
                'https://spreadsheets.google.com/feeds',
                'https://www.googleapis.com/auth/drive'
            ]
            
            creds = ServiceAccountCredentials.from_json_keyfile_name('credentials.json', scope)
            client = gspread.authorize(creds)
            
            # Открываем таблицу
            self.spreadsheet = client.open_by_key(self.spreadsheet_id)
            
            # Получаем или создаем лист "Счета"
            try:
                self.sheet = self.spreadsheet.worksheet('Счета')
                logger.info("✅ Лист 'Счета' найден")
            except:
                logger.info("📝 Создаем лист 'Счета'...")
                self.sheet = self.spreadsheet.add_worksheet(title='Счета', rows=1000, cols=10)
                # Заголовки
                headers = ['ID', 'Номер счета', 'Дата', 'Поставщик', 'Сумма', 'Назначение', 'Приоритет', 'Время добавления']
                self.sheet.append_row(headers)
                logger.info("✅ Заголовки созданы")
            
            logger.info(f"✅ Google Sheets подключен: {self.spreadsheet.title}")
            
        except Exception as e:
            logger.error(f"❌ Ошибка подключения Google Sheets: {e}")
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
        return gs_manager is not None
    except Exception as e:
        logger.warning(f"⚠️ Google Sheets отключен: {e}")
        return False
