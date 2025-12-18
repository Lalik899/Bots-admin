import sqlite3
import requests
from xml.etree import ElementTree

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

BOT_TOKEN = "токен"
ADMIN_USER_ID = айди админа


# ================== БАЗА ДАННЫХ ==================
def init_db():
    conn = sqlite3.connect("id.db")
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS Пользователи (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            id_user INTEGER UNIQUE,
            first_name TEXT,
            last_name TEXT,
            user_name TEXT
            
        )
    """)
    conn.commit()
    conn.close()


# ================== КУРС ВАЛЮТ ==================
def get_currency_rates():
    url = "https://www.cbr.ru/scripts/XML_daily.asp"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        tree = ElementTree.fromstring(response.content)
        rates = {}

        for valute in tree.findall("Valute"):
            char = valute.find("CharCode").text
            value = float(valute.find("Value").text.replace(",", "."))
            rates[char] = value

        text = (
            "💱 Курс валют:\n\n"
            f"💵 USD: {rates.get('USD', '—')} ₽\n"
            f"💶 EUR: {rates.get('EUR', '—')} ₽\n"
            f"💴 CNY: {rates.get('CNY', '—')} ₽\n"
            f"🇰🇿 KZT: {rates.get('KZT', '—')} ₽"
        )
        return text

    except Exception:
        return "Не удалось получить курс валют"


# ================== /start ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    keyboard = [
        [InlineKeyboardButton("Регистрация", callback_data="register")],
        [InlineKeyboardButton("Изменить данные", callback_data="edit")],
        [InlineKeyboardButton("Валюта", callback_data="currency")]
    ]

    if user_id == ADMIN_USER_ID:
        keyboard.append(
            [InlineKeyboardButton("Все пользователи", callback_data="show_all")]
        )

    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# ================== КНОПКИ ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = user.id

    conn = sqlite3.connect("id.db")
    cur = conn.cursor()

    # ---------- ВАЛЮТА ----------
    if query.data == "currency":
        await query.edit_message_text(get_currency_rates())

    # ---------- РЕГИСТРАЦИЯ ----------
    elif query.data == "register":
        cur.execute("SELECT 1 FROM Пользователи WHERE id_user = ?", (user_id,))
        if cur.fetchone():
            text = "Вы уже зарегистрированы"
        else:
            cur.execute(
                "INSERT INTO Пользователи (id_user, first_name, last_name, user_name) VALUES (?, ?, ?, ?)",
                (
                    user_id,
                    user.first_name,
                    user.username or "нет",
                    user.last_name or ""
                )
            )
            conn.commit()
            text = "Регистрация успешна!"

        await query.edit_message_text(text)

    # ---------- ВСЕ ПОЛЬЗОВАТЕЛИ ----------
    elif query.data == "show_all":
        if user_id != ADMIN_USER_ID:
            await query.edit_message_text("Нет доступа")
        else:
            cur.execute("SELECT * FROM Пользователи")
            users = cur.fetchall()

            if not users:
                text = "База пуста"
            else:
                text = "Пользователи:\n\n"
                for u in users:
                    text += (
                        f"ID: {u[1]}\n"
                        f"Имя: {u[2]}\n"
                        f"Username: @{u[3]}\n"
                        f"Фамилия: {u[4]}\n"
                        f"{'-'*20}\n"
)

            await query.edit_message_text(text)

    # ---------- РЕДАКТИРОВАНИЕ ----------
    elif query.data == "edit":
        cur.execute("SELECT 1 FROM Пользователи WHERE id_user = ?", (user_id,))
        if not cur.fetchone():
            await query.edit_message_text("Сначала зарегистрируйтесь")
        else:
            context.user_data["edit"] = True
            await query.edit_message_text(
                "Введите данные:\n\n"
                "Имя, Фамилия, Username\n\n"
                "Пример:\nИван, Иванов, ivan123"
            )

    conn.close()


# ================== ОБНОВЛЕНИЕ ДАННЫХ ==================
async def edit_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get("edit"):
        return

    try:
        first_name, username, last_name = map(str.strip, update.message.text.split(","))

        conn = sqlite3.connect("id.db")
        cur = conn.cursor()
        cur.execute(
            """
            UPDATE Пользователи
            SET first_name=?, last_name=?, user_name=?
            WHERE id_user=?
            """,
            (first_name, username, last_name, update.effective_user.id)
        )
        conn.commit()
        conn.close()

        context.user_data["edit"] = False
        await update.message.reply_text("Данные обновлены")

    except ValueError:
        await update.message.reply_text("Неверный формат")


# ================== ЗАПУСК ==================
def main():
    init_db()

    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, edit_user_data))

    print("Бот запущен")
    app.run_polling()


if __name__ == "__main__":
    main()
