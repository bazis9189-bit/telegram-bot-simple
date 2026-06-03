# -*- coding: utf-8 -*-
"""
Telegram-бот СКБ — заявки на ТМЦ.
Этап 1: мастер выбирает себя → топ-позиции/категории/поиск → количество →
срочность → отправка сводной заявки руководителю.

Запуск: задайте переменные окружения BOT_TOKEN и BOSS_ID, затем `python bot.py`.
"""

import os
import logging
from datetime import datetime

from telegram import (
    Update,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from data import (
    MASTERS,
    CITY_ORDER,
    CATEGORIES,
    CATEGORY_EMOJI,
    ALL_ITEMS,
)

# ── Конфигурация из окружения ──────────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN", "").strip()
BOSS_ID = os.environ.get("BOSS_ID", "").strip()

if not BOT_TOKEN:
    raise SystemExit("Не задан BOT_TOKEN. Установите переменную окружения BOT_TOKEN.")
if not BOSS_ID:
    raise SystemExit("Не задан BOSS_ID. Установите переменную окружения BOSS_ID.")
BOSS_ID = int(BOSS_ID)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
log = logging.getLogger("skb_bot")

# Список категорий с индексами (callback не любит длинные строки)
CAT_LIST = list(CATEGORIES.keys())


# ── Хелперы для состояния пользователя ─────────────────────────────────────
def get_cart(context: ContextTypes.DEFAULT_TYPE) -> dict:
    """Корзина: {item_name: {"qty": int, "urgent": bool}}."""
    return context.user_data.setdefault("cart", {})


def cart_summary(context) -> str:
    cart = get_cart(context)
    if not cart:
        return ""
    total = len(cart)
    urgent = sum(1 for v in cart.values() if v["urgent"])
    s = f"🛒 В заявке: {total} поз."
    if urgent:
        s += f" · ⚡ {urgent} срочных"
    return s


# ── /start ─────────────────────────────────────────────────────────────────
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await show_master_menu(update, context)


async def show_master_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = []
    for city in CITY_ORDER:
        keyboard.append([InlineKeyboardButton(f"📍 {city}", callback_data="noop")])
        for key, m in MASTERS.items():
            if m["city"] == city:
                star = " ⭐" if m["top"] else ""
                keyboard.append([
                    InlineKeyboardButton(f"   {m['label']}{star}", callback_data=f"master:{key}")
                ])
    text = (
        "👷 *СКБ — Заявка на ТМЦ*\n\n"
        "Выберите себя из списка. Ваши часто заказываемые позиции "
        "загрузятся первыми."
    )
    markup = InlineKeyboardMarkup(keyboard)
    if update.callback_query:
        await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")
    else:
        await update.message.reply_text(text, reply_markup=markup, parse_mode="Markdown")


# ── Выбор мастера ──────────────────────────────────────────────────────────
async def on_master(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    key = q.data.split(":", 1)[1]
    context.user_data["master"] = key
    get_cart(context).clear()
    await show_main_menu(update, context)


async def show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data["master"]
    m = MASTERS[key]
    keyboard = []
    if m["top"]:
        keyboard.append([InlineKeyboardButton("⭐ Часто заказываю", callback_data="top")])
    for i, cat in enumerate(CAT_LIST):
        emoji = CATEGORY_EMOJI.get(cat, "📦")
        keyboard.append([InlineKeyboardButton(f"{emoji} {cat}", callback_data=f"cat:{i}")])
    keyboard.append([InlineKeyboardButton("🔍 Поиск позиции", callback_data="search")])
    keyboard.append([InlineKeyboardButton("➕ Добавить свою позицию", callback_data="custom")])

    cart = get_cart(context)
    if cart:
        keyboard.append([InlineKeyboardButton(f"✅ Оформить заявку ({len(cart)})", callback_data="review")])
    keyboard.append([InlineKeyboardButton("« Сменить мастера", callback_data="back_master")])

    text = f"*{m['label']}*\n{m['object']}\n\n"
    summ = cart_summary(context)
    if summ:
        text += summ + "\n\n"
    text += "Выберите раздел или начните добавлять позиции:"

    await update.callback_query.edit_message_text(
        text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown"
    )


# ── Показ списка позиций (топ / категория / поиск) ─────────────────────────
def build_items_keyboard(context, items, source):
    """source кодирует, откуда вернуться: 'top', 'cat:N', 'search'."""
    cart = get_cart(context)
    keyboard = []
    for idx, item in enumerate(items):
        in_cart = cart.get(item)
        if in_cart:
            mark = f"✅{in_cart['qty']}"
            if in_cart["urgent"]:
                mark += "⚡"
            label = f"{mark} {item}"
        else:
            label = item
        # callback: pick|<source>|<idx>
        keyboard.append([InlineKeyboardButton(label[:60], callback_data=f"pick|{source}|{idx}")])
    keyboard.append([InlineKeyboardButton("« Назад в меню", callback_data="menu")])
    return InlineKeyboardMarkup(keyboard)


def items_for_source(context, source):
    if source == "top":
        key = context.user_data["master"]
        return MASTERS[key]["top"]
    if source.startswith("cat:"):
        i = int(source.split(":")[1])
        return CATEGORIES[CAT_LIST[i]]
    if source == "search":
        return context.user_data.get("search_results", [])
    return []


async def show_items(update, context, source, title):
    items = items_for_source(context, source)
    context.user_data["last_source"] = source
    markup = build_items_keyboard(context, items, source)
    text = f"*{title}*\n\nНажмите на позицию, чтобы указать количество."
    summ = cart_summary(context)
    if summ:
        text = f"{summ}\n\n" + text
    await update.callback_query.edit_message_text(text, reply_markup=markup, parse_mode="Markdown")


async def on_top(update, context):
    await update.callback_query.answer()
    await show_items(update, context, "top", "⭐ Часто заказываю")


async def on_cat(update, context):
    await update.callback_query.answer()
    i = int(update.callback_query.data.split(":")[1])
    cat = CAT_LIST[i]
    emoji = CATEGORY_EMOJI.get(cat, "📦")
    await show_items(update, context, f"cat:{i}", f"{emoji} {cat}")


# ── Нажатие на позицию → спросить количество ───────────────────────────────
async def on_pick(update, context):
    q = update.callback_query
    await q.answer()
    _, source, idx = q.data.split("|")
    items = items_for_source(context, source)
    item = items[int(idx)]
    context.user_data["awaiting_qty_for"] = item
    context.user_data["awaiting_return"] = source
    cart = get_cart(context)
    current = cart.get(item, {}).get("qty", "")
    hint = f" (сейчас: {current})" if current else ""
    await q.edit_message_text(
        f"Позиция:\n*{item}*\n\nВведите количество числом{hint}.\n"
        f"Чтобы убрать из заявки — отправьте 0.",
        parse_mode="Markdown",
    )


# ── Поиск ──────────────────────────────────────────────────────────────────
async def on_search(update, context):
    q = update.callback_query
    await q.answer()
    context.user_data["awaiting_search"] = True
    await q.edit_message_text(
        "🔍 Введите часть названия позиции (например: «мешки» или «перчатки»):"
    )


# ── Своя позиция ───────────────────────────────────────────────────────────
async def on_custom(update, context):
    q = update.callback_query
    await q.answer()
    context.user_data["awaiting_custom"] = True
    await q.edit_message_text(
        "➕ Введите название новой позиции и количество в одном сообщении.\n\n"
        "Например: `Швабра с отжимом 5`\n\n"
        "Можно прикрепить фото — отправьте его *следующим* сообщением с подписью-названием.",
        parse_mode="Markdown",
    )


# ── Обработка текстовых сообщений (кол-во / поиск / своя позиция) ───────────
async def on_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()

    # Ожидаем количество для выбранной позиции
    if context.user_data.get("awaiting_qty_for"):
        item = context.user_data.pop("awaiting_qty_for")
        source = context.user_data.pop("awaiting_return", "menu")
        try:
            qty = int(text)
        except ValueError:
            context.user_data["awaiting_qty_for"] = item
            context.user_data["awaiting_return"] = source
            await update.message.reply_text("Нужно число. Попробуйте ещё раз:")
            return
        cart = get_cart(context)
        if qty <= 0:
            cart.pop(item, None)
            await update.message.reply_text(f"Убрано: {item}")
        else:
            urgent = cart.get(item, {}).get("urgent", False)
            cart[item] = {"qty": qty, "urgent": urgent}
            await update.message.reply_text(f"✅ {item} — {qty} шт")
        await send_quick_menu(update, context)
        return

    # Ожидаем поисковый запрос
    if context.user_data.get("awaiting_search"):
        context.user_data.pop("awaiting_search")
        ql = text.lower()
        results = [it for it in ALL_ITEMS if ql in it.lower()]
        context.user_data["search_results"] = results
        if not results:
            await update.message.reply_text("Ничего не найдено. Откройте меню /menu и попробуйте снова.")
            return
        await send_search_results(update, context, results)
        return

    # Ожидаем свою позицию
    if context.user_data.get("awaiting_custom"):
        context.user_data.pop("awaiting_custom")
        # пытаемся отделить число с конца
        parts = text.rsplit(" ", 1)
        if len(parts) == 2 and parts[1].isdigit():
            name, qty = parts[0], int(parts[1])
        else:
            name, qty = text, 1
        name = "🆕 " + name
        get_cart(context)[name] = {"qty": qty, "urgent": False}
        await update.message.reply_text(f"✅ Добавлено: {name} — {qty} шт")
        await send_quick_menu(update, context)
        return

    # Иначе подсказка
    await update.message.reply_text("Откройте меню командой /menu")


async def on_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Фото для своей позиции — сохраняем file_id и подпись."""
    caption = (update.message.caption or "").strip()
    photo = update.message.photo[-1].file_id
    name = "🆕 " + (caption if caption else "Позиция с фото")
    photos = context.user_data.setdefault("photos", {})
    photos[name] = photo
    get_cart(context).setdefault(name, {"qty": 1, "urgent": False})
    await update.message.reply_text(f"📷 Фото сохранено к позиции: {name}")
    await send_quick_menu(update, context)


# ── Вспомогательные клавиатуры после действий ──────────────────────────────
async def send_quick_menu(update, context):
    cart = get_cart(context)
    keyboard = [[InlineKeyboardButton("« В меню", callback_data="menu")]]
    if cart:
        keyboard.insert(0, [InlineKeyboardButton(f"✅ Оформить заявку ({len(cart)})", callback_data="review")])
    await update.message.reply_text(
        cart_summary(context) or "Заявка пока пуста.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def send_search_results(update, context, results):
    cart = get_cart(context)
    keyboard = []
    for idx, item in enumerate(results[:40]):
        in_cart = cart.get(item)
        label = (f"✅{in_cart['qty']} " if in_cart else "") + item
        keyboard.append([InlineKeyboardButton(label[:60], callback_data=f"pick|search|{idx}")])
    keyboard.append([InlineKeyboardButton("« В меню", callback_data="menu")])
    await update.message.reply_text(
        f"Найдено: {len(results)}. Нажмите на позицию:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ── Просмотр и оформление заявки ───────────────────────────────────────────
async def on_review(update, context):
    q = update.callback_query
    await q.answer()
    cart = get_cart(context)
    if not cart:
        await q.answer("Заявка пуста", show_alert=True)
        return
    keyboard = []
    for item, v in cart.items():
        mark = "⚡" if v["urgent"] else "☐"
        keyboard.append([
            InlineKeyboardButton(f"{mark} {item} — {v['qty']}шт"[:55], callback_data="noop"),
            InlineKeyboardButton("⚡" if not v["urgent"] else "✓", callback_data=f"urg|{item}"),
        ])
    keyboard.append([InlineKeyboardButton("📨 ОТПРАВИТЬ заявку", callback_data="send")])
    keyboard.append([InlineKeyboardButton("« Добавить ещё", callback_data="menu")])

    urgent = sum(1 for v in cart.values() if v["urgent"])
    text = (
        f"*Проверьте заявку*\n\n"
        f"Позиций: {len(cart)}"
        + (f" · ⚡ срочных: {urgent}" if urgent else "")
        + "\n\nКнопкой ⚡ справа можно пометить позицию срочной."
    )
    await q.edit_message_text(text, reply_markup=InlineKeyboardMarkup(keyboard), parse_mode="Markdown")


async def on_toggle_urgent(update, context):
    q = update.callback_query
    item = q.data.split("|", 1)[1]
    cart = get_cart(context)
    if item in cart:
        cart[item]["urgent"] = not cart[item]["urgent"]
    await q.answer("Готово")
    await on_review(update, context)


# ── Отправка заявки руководителю ───────────────────────────────────────────
async def on_send(update, context):
    q = update.callback_query
    await q.answer()
    cart = get_cart(context)
    if not cart:
        await q.answer("Заявка пуста", show_alert=True)
        return
    key = context.user_data["master"]
    m = MASTERS[key]
    user = q.from_user
    now = datetime.now().strftime("%d.%m.%Y %H:%M")

    urgent_items = [(i, v) for i, v in cart.items() if v["urgent"]]
    normal_items = [(i, v) for i, v in cart.items() if not v["urgent"]]

    lines = [
        "📦 *НОВАЯ ЗАЯВКА НА ТМЦ*",
        "",
        f"👷 Мастер: *{m['label']}*",
        f"🏭 Объект: {m['object']}",
        f"🕐 {now}",
        f"👤 @{user.username or user.first_name} (id {user.id})",
        "",
    ]
    if urgent_items:
        lines.append("⚡ *СРОЧНО:*")
        for i, v in urgent_items:
            lines.append(f"  • {i} — *{v['qty']} шт*")
        lines.append("")
    lines.append("📋 *Позиции:*")
    for i, v in normal_items:
        lines.append(f"  • {i} — {v['qty']} шт")
    lines.append("")
    lines.append(f"Итого позиций: {len(cart)}")

    boss_text = "\n".join(lines)

    # Отправляем руководителю
    await context.bot.send_message(BOSS_ID, boss_text, parse_mode="Markdown")
    # Фото своих позиций, если есть
    photos = context.user_data.get("photos", {})
    for name, file_id in photos.items():
        if name in cart:
            try:
                await context.bot.send_photo(BOSS_ID, file_id, caption=name)
            except Exception as e:
                log.warning("Не удалось отправить фото: %s", e)

    # Подтверждение мастеру
    await q.edit_message_text(
        "✅ *Заявка отправлена!*\n\n"
        f"Передано руководителю: {len(cart)} позиций"
        + (f", из них ⚡ срочных: {len(urgent_items)}" if urgent_items else "")
        + "\n\nНовая заявка — /start",
        parse_mode="Markdown",
    )
    # Чистим корзину
    get_cart(context).clear()
    context.user_data.pop("photos", None)


# ── Навигация ──────────────────────────────────────────────────────────────
async def on_menu(update, context):
    await update.callback_query.answer()
    await show_main_menu(update, context)


async def on_back_master(update, context):
    await update.callback_query.answer()
    await show_master_menu(update, context)


async def on_noop(update, context):
    await update.callback_query.answer()


async def menu_command(update, context):
    if "master" not in context.user_data:
        await show_master_menu(update, context)
    else:
        # имитируем callback-меню через обычное сообщение
        key = context.user_data["master"]
        m = MASTERS[key]
        keyboard = [[InlineKeyboardButton("Открыть меню", callback_data="menu")]]
        await update.message.reply_text(
            f"{m['label']} — нажмите, чтобы открыть меню:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


# ── Точка входа ────────────────────────────────────────────────────────────
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", menu_command))

    app.add_handler(CallbackQueryHandler(on_master, pattern=r"^master:"))
    app.add_handler(CallbackQueryHandler(on_top, pattern=r"^top$"))
    app.add_handler(CallbackQueryHandler(on_cat, pattern=r"^cat:"))
    app.add_handler(CallbackQueryHandler(on_pick, pattern=r"^pick\|"))
    app.add_handler(CallbackQueryHandler(on_search, pattern=r"^search$"))
    app.add_handler(CallbackQueryHandler(on_custom, pattern=r"^custom$"))
    app.add_handler(CallbackQueryHandler(on_review, pattern=r"^review$"))
    app.add_handler(CallbackQueryHandler(on_toggle_urgent, pattern=r"^urg\|"))
    app.add_handler(CallbackQueryHandler(on_send, pattern=r"^send$"))
    app.add_handler(CallbackQueryHandler(on_menu, pattern=r"^menu$"))
    app.add_handler(CallbackQueryHandler(on_back_master, pattern=r"^back_master$"))
    app.add_handler(CallbackQueryHandler(on_noop, pattern=r"^noop$"))

    app.add_handler(MessageHandler(filters.PHOTO, on_photo))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, on_text))

    log.info("Бот запущен.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
