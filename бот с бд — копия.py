import sqlite3
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters
)

BOT_TOKEN = ''
ADMIN_USER_ID = 7581886369


# ================== ИНИЦИАЛИЗАЦИЯ БАЗЫ ДАННЫХ ==================
def init_db():
    connection = sqlite3.connect('id.db')
    cursor = connection.cursor()
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS Пользователи (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        id_user INTEGER UNIQUE,
        first_name TEXT NOT NULL,
        user_name TEXT NOT NULL,
        last_name TEXT
    )
    ''')
    connection.commit()
    connection.close()


def get_currency_rates():
    url = "https://www.cbr.ru/scripts/XML_daily.asp"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()  # выбросит ошибку, если HTTP != 200
        data_json = response.json()
        
        # Проверяем, есть ли ключ 'rates'
        if "rates" not in data_json:
            return "❌ Не удалось получить курс валют. Попробуйте позже."
        
        data = data_json["rates"]
        text = (
            "💱 Курс валют (обновляется ежедневно):\n\n"
            f"💵 Доллар (USD): {data.get('USD', 0):.2f} ₽\n"
            f"💶 Евро (EUR): {data.get('EUR', 0):.2f} ₽\n"
            f"💴 Юань (CNY): {data.get('CNY', 0):.2f} ₽\n"
            f"🇰🇿 Тенге (KZT): {data.get('KZT', 0):.2f} ₽"
        )
        return text

    except requests.RequestException:
        return "❌ Ошибка при подключении к API. Попробуйте позже."
# ================== КОМАНДА /start ==================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id

    keyboard = [
        [InlineKeyboardButton("Регистрация", callback_data='register')],
        [InlineKeyboardButton("Изменить мои данные", callback_data='edit')],
        [InlineKeyboardButton("💱 Валюта", callback_data='currency')]

    ]
    
        
    # Если админ — показываем кнопку просмотра всех
    if user_id == ADMIN_USER_ID:
        keyboard.append(
            [InlineKeyboardButton("Показать всех пользователей", callback_data='show_all')]
        )

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Выберите действие:",
        reply_markup=reply_markup
    )

    
# ================== ОБРАБОТКА КНОПОК ==================
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_id = user.id
# ---------- КУРС ВАЛЮТ ----------
    if query.data == 'currency':
        text = get_currency_rates()
        await query.edit_message_text(text=text)
    

    connection = sqlite3.connect('id.db')
    cursor = connection.cursor()
    

    # ---------- РЕГИСТРАЦИЯ ----------
    if query.data == 'register':
        cursor.execute('SELECT 1 FROM Пользователи WHERE id_user = ?', (user_id,))
        exists = cursor.fetchone()

        
        
        if exists:
            text = " Вы уже зарегистрированы"
        else:
            cursor.execute(
                'INSERT INTO Пользователи (id_user, first_name, user_name, last_name) VALUES (?, ?, ?, ?)',
                (
                    user_id,
                    user.first_name,
                    user.username or "Нет username",
                    user.last_name or ""
                )
            )
            connection.commit()
            text = f"✅ Регистрация успешна, {user.first_name}!"

        await query.edit_message_text(text=text)

    # ---------- ПРОСМОТР ВСЕХ (ТОЛЬКО АДМИН) ----------
    elif query.data == 'show_all':
        if user_id != ADMIN_USER_ID:
            await query.edit_message_text(" У вас нет прав доступа")
        else:
            cursor.execute('SELECT * FROM Пользователи')
            users = cursor.fetchall()

            if not users:
                text = "База данных пуста"
            else:
                text = " Все зарегистрированные пользователи:\n\n"
                for u in users:
                    text += (
                        f"ID: {u[1]}\n"
                        f"Имя: {u[2]}\n"
                        f"Username: @{u[3]}\n"
                        f"Фамилия: {u[4]}\n"
                        f"{'-'*20}\n"
                    )

            await query.edit_message_text(text=text)
    

    # ---------- ИЗМЕНЕНИЕ ДАННЫХ ----------
    elif query.data == 'edit':
        cursor.execute('SELECT 1 FROM Пользователи WHERE id_user = ?', (user_id,))
        exists = cursor.fetchone()

        if not exists:
            await query.edit_message_text(" Сначала зарегистрируйтесь")
        else:
            context.user_data['edit'] = True
            await query.edit_message_text(
                "✏️ Отправьте новые данные в формате:\n\n"
                "Имя, фамилия, username\n\n"
                "Пример:\nИван, Иванов, ivan123"
            )

    connection.close()

# ================== ПОЛУЧЕНИЕ НОВЫХ ДАННЫХ ==================
async def edit_user_data(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.user_data.get('edit'):
        return

    try:
        first_name, username, last_name = map(str.strip, update.message.text.split(','))

        connection = sqlite3.connect('id.db')
        cursor = connection.cursor()
        cursor.execute(
            '''
            UPDATE Пользователи
            SET first_name = ?, user_name = ?, last_name = ?
            WHERE id_user = ?
            ''',
            (first_name, username, last_name, update.message.from_user.id)
        )
        connection.commit()
        connection.close()

        context.user_data['edit'] = False
        await update.message.reply_text(" Данные успешно обновлены")

    except ValueError:
        await update.message.reply_text(" Неверный формат")


    
# ================== ЗАПУСК БОТА ==================
def main():
    init_db()
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler('start', start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, edit_user_data))

    application.run_polling()


if __name__ == '__main__':
    main()
