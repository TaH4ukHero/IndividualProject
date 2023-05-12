import json
import logging
import random
from telegram import Update, ReplyKeyboardRemove, Bot, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ConversationHandler, MessageHandler, filters, \
    ContextTypes
from config import BOT_TOKEN
# from dotenv import dotenv_values FOR Glitch
from data.db_session import global_init, create_session
from data.users import User
from useful_func import *

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.DEBUG
)

logger = logging.getLogger(__name__)

# Словесное представление states для # conv_handler

LAUNCH_DIALOG, LETTER_OR_TOWN, LETTER, TOWN, HINT = range(5)
"""
   LAUNCH_DIALOG - Начать игру или нет
   LETTER_OR_TOWN - Выбор способа угадывания (по одной букве или целым словом)
   LETTER - При выборе угадывания по одной букве
   TOWN - При выборе угадывания целым словом
"""

# Список городов для загадывания

towns = [i.strip("\n") for i in open('true_towns.txt', encoding='utf8')]

# Города с которыми возникали проблемы
towns_exceptions = ["Йошкар-Ола", 'Каменск-Уральский', 'Комсомольск-на-Амуре', 'Орехово-Зуево',
                    'Петропавловск-Камчатский', 'Ростов-на-Дону', 'Санкт-Петербург', 'Улан-Удэ',
                    'Ханты-Мансийск', 'Южно-Сахалинск']

status = ["Отгадывание буквы", 'Отгадывание слова целиком', 'Выбор подсказки', 'Выбор режима игры']
guess_letter, guess_word, choice_hint, choice_gamemode = status


async def start(update, context: ContextTypes.DEFAULT_TYPE) -> LAUNCH_DIALOG:
    user = update.effective_user
    keyboard = [['ДА', 'НЕТ']]
    # keyboard = [[InlineKeyboardButton('ДА')], [InlineKeyboardButton('НЕТ')]]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)
    await update.message.reply_html(
        f"Привет {user.mention_html()}! Я игровой бот. Не хочешь сыграть в <b>Угадай город?</b>",
        reply_markup=markup
    )
    return LAUNCH_DIALOG


async def launch(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message.text == 'ДА':
        keyboard = ReplyKeyboardMarkup([['Назову букву', 'Назову город целиком']],
                                       one_time_keyboard=True, resize_keyboard=True)
        context.user_data['guessed_town'] = list(random.choice(towns).replace(' ', '-'))
        context.user_data["guessed_letters"] = list()
        context.user_data["not_guessed_letters"] = context.user_data["guessed_town"][::]
        context.user_data["hints"] = 3
        context.user_data['status'] = choice_gamemode
        await update.message.reply_text('Хорошо, сыграем! Я загадал, попробуй угадать! У '
                                        'тебя есть 3 подсказки.')
        await update.message.reply_text('Выбери один из вариантов.', reply_markup=keyboard)
        return LETTER_OR_TOWN
    elif update.message.text == 'НЕТ':
        keyboard = ReplyKeyboardMarkup([['/start', '/help', '/stats']], resize_keyboard=True)
        await update.message.reply_text('Жаль. До скорой встречи!',
                                        reply_markup=keyboard)

        return ConversationHandler.END
    await update.message.reply_text('Выберите команду из предложенных кнопок на клавиатуре')
    return LAUNCH_DIALOG


async def letter_or_town(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message.text
    keyboard = ReplyKeyboardMarkup([['Назову букву', 'Назову город целиком'],
                                    ['Подсказка', 'Помощь', 'Статус игры']],
                                   one_time_keyboard=True, resize_keyboard=True)
    if msg == 'Статус игры':
        await status(update, context)
    if msg == 'Помощь':
        await help_(update, context)
    if msg == 'Назову букву':
        await update.message.reply_html(
            'Хорошо! Называй букву из названия города.\nУгаданные буквы\n'
            f'<b>{" ".join(print_guessed_letters(context)).capitalize()}</b>', reply_markup=keyboard)
        return LETTER
    elif msg == 'Назову город целиком':
        await update.message.reply_text('Хорошо! Называй название города целиком.',
                                        reply_markup=keyboard)
        return TOWN
    await update.message.reply_text('Выберите команду из предложенных кнопок на клавиатуре')


async def hint(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message.text
    user_data = context.user_data
    user_data["status"] = choice_hint
    keyboard = ReplyKeyboardMarkup([['Назову букву', 'Назову город целиком'],
                                    ['Помощь', 'Статус игры']],
                                   one_time_keyboard=True, resize_keyboard=True)
    if msg == 'Статус игры':
        await status(update, context)
        return HINT
    if msg == 'Помощь':
        await help_(update, context)
        return HINT
    if user_data["hints"] <= 0:
        await update.message.reply_text('Подсказок больше нет', reply_markup=keyboard)
        return LETTER_OR_TOWN
    if msg == 'Назвать административный округ':
        with open('town2AdmArea.json', encoding='utf8') as f:
            admArea = json.load(f)[''.join(user_data["guessed_town"])]
            user_data["hints"] -= 1
            text = admArea
            await update.message.reply_text(f"{text}\nОсталось подсказок {user_data['hints']}/3",
                                            reply_markup=keyboard)
    elif msg == 'Открыть букву':
        user_data["hints"] -= 1
        await update.message.reply_text(f'Была открыта новая буква\nОсталось подсказок '
                                        f'{user_data["hints"]}/3', reply_markup=keyboard)
        user_data = hint_2(random.choice(user_data["not_guessed_letters"]), user_data)
        if " ".join(print_guessed_letters(context)).count('_') == 0:
            win_params = win(context)
            await update.message.reply_html(win_params[2])
            await update.message.reply_html(win_params[1], reply_markup=win_params[0])
            fix_results(update, context, 'WIN')
            return LAUNCH_DIALOG
        await update.message.reply_html(f'Угаданные буквы\n'
                                        f'<b>{" ".join(print_guessed_letters(context))}</b>')
    else:
        await update.message.reply_text('Выберите команду из предложенных кнопок на клавиатуре')
    return LETTER_OR_TOWN


async def check_letter(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    msg = update.message.text
    user_data = context.user_data
    user_data["status"] = guess_letter
    if msg == 'Статус игры':
        await status(update, context)
        return LETTER
    if msg == 'Помощь':
        await help_(update, context)
        return LETTER
    if msg == 'Подсказка':
        await update.message.reply_text(keyboard_for_hint()[1], reply_markup=keyboard_for_hint()[0])
        return HINT
    if msg == 'Назову город целиком':
        await update.message.reply_text('Хорошо! Называй название города целиком.')
        return TOWN
    if msg == 'Назову букву':
        return
    user_data["attempts"] = user_data.get("attempts", 0) + 1  # Добавление попытки в общее кол-во
    if len(msg) == 1 and msg.isalpha() and msg.lower() not in user_data["guessed_letters"]:
        user_data["guessed_letters"].append(msg.lower())
        if " ".join(print_guessed_letters(context)).count('_') == 0:
            win_params = win(context)
            await update.message.reply_html(win_params[2])
            await update.message.reply_html(win_params[1], reply_markup=win_params[0])
            fix_results(update, context, 'WIN')
            return LAUNCH_DIALOG
        if msg.lower() in user_data["guessed_town"] or msg in user_data[
            "guessed_town"]:
            await update.message.reply_text('Отлично! Эта буква есть в названии.')
            user_data["not_guessed_letters"] = hint_2(msg, user_data)["not_guessed_letters"]
    elif len(msg) > 1:
        await update.message.reply_text('Вводи по одной букве!')
    else:
        await update.message.reply_text('Эта буква уже использовалась! Попробуй другую')
    await update.message.reply_html(f'Угаданные буквы\n'
                                    f'<b>{" ".join(print_guessed_letters(context))}</b>')


async def check_town(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_data = context.user_data
    msg = update.message.text
    user_data["status"] = guess_word
    if msg == 'Статус игры':
        await status(update, context)
        return TOWN
    if msg == 'Помощь':
        await help_(update, context)
        return TOWN
    if msg == 'Подсказка':
        await update.message.reply_text(keyboard_for_hint()[1], reply_markup=keyboard_for_hint()[0])
        return HINT
    if msg == 'Назову букву':
        await update.message.reply_html('Хорошо! Называй букву из названия города.\n'
                                        'Угаданные буквы\n'
                                        f'<b>{" ".join(print_guessed_letters(context))}</b>')
        return LETTER
    if msg == 'Назову город целиком':
        return
    user_data["attempts"] = user_data.get("attempts", 0) + 1  # Добавление попытки в общее кол-во
    if msg.lower() == ''.join(user_data["guessed_town"]).lower().replace(
            '-', ' ') or msg.lower() == ''.join(user_data["guessed_town"]).lower():
        win_params = win(context)
        await update.message.reply_html(win_params[2])
        await update.message.reply_html(win_params[1], reply_markup=win_params[0])
        fix_results(update, context, 'WIN')
        return LAUNCH_DIALOG
    else:
        await update.message.reply_text('К сожалению, это неправильный ответ. Попробуй еще раз!',
                                        reply_markup=ReplyKeyboardMarkup(
                                            [['Назову букву', 'Назову город целиком'],
                                             ['Подсказка', 'Помощь']],
                                            one_time_keyboard=True, resize_keyboard=True))


# Функция для теста
async def dev(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(''.join(context.user_data['guessed_town']))
    await update.message.reply_text(''.join(context.user_data["not_guessed_letters"]))
    await update.message.reply_text(''.join(context.user_data['guessed_letters']))


# Функция для прощания
async def bye(update: Update, context: ContextTypes.DEFAULT_TYPE) -> ConversationHandler.END:
    await update.message.reply_text('Жаль, что не смог победить! Спасибо за игру! Жду снова!',
                                    reply_markup=ReplyKeyboardMarkup([['/start', '/help', '/stats']],
                                                                     resize_keyboard=True))
    fix_results(update, context, "LOSE")
    return ConversationHandler.END


async def get_photo(update: Update) -> bool:  # Получения фото пользователя
    photo = await bot.get_user_profile_photos(update.effective_user.id)
    try:
        photo = photo.photos[0][0]
    except IndexError:
        return False
    file = await bot.get_file(photo.file_id)
    await file.download_to_drive(f'data/photos/{update.effective_user.id}.jpeg')
    return True


async def statistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    sess = create_session()
    user = sess.query(User).filter(User.user_id == update.effective_user.id).first()
    if user is None:
        user = User()
        user.user_id = update.effective_user.id
        sess.add(user)
        sess.commit()
        user = sess.query(User).filter(User.user_id == update.effective_user.id).first()
    if await get_photo(update):
        await update.message.reply_photo(f'data/photos/{update.effective_user.id}.jpeg')
    await update.message.reply_html(
        f"<b>Статистика игрока  {update.effective_user.mention_html()}</b>\n"
        f"<b>Победы - {user.wins}</b>\n<b>Поражения - {user.loses}</b>\n"
        f"<b>Наибольшее кол-во попыток для угадывания - {user.most_attempts}</b>\n"
        f"<b>Наименьшее кол-во попыток для угадывания - {user.min_attempts}</b>\n"
        f"<b>Последнее кол-во попыток для угадывания - {user.wins}</b>\n"
        f"<b>Всего попыток - {user.attempts}</b>")


async def help_(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_html('<b>/start - Начало игры</b>\n\n'
                                    '<b>/stats - Статистика игрока</b>\n\n'
                                    '<b>/stop - Конец игры при уже запущенной игре</b>')


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if context.user_data.get("status", 0):
        await update.message.reply_html(f'В данный момент ты на стадии игры:\n'
                                        f'<b>{context.user_data["status"]}</b>')
    else:
        await update.message.reply_text("В данный момент ты не играешь.\nНачало игры - /start")


if __name__ == '__main__':
    app = Application.builder().token(BOT_TOKEN).build()
    # app = Application.builder().token(dotenv_values()["BOT_TOKEN"]) FOR Glitch
    bot = Bot(BOT_TOKEN)
    # bot = Bot(dotenv_values()["BOT_TOKEN"]) FOR Glitch

    global_init('db/user.db')

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            LAUNCH_DIALOG: [MessageHandler(filters.TEXT & ~filters.COMMAND, launch)],
            LETTER_OR_TOWN: [MessageHandler(filters.TEXT & ~filters.COMMAND, letter_or_town),
                             CommandHandler('stop', bye)],
            LETTER: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_letter),
                     CommandHandler('stop', bye)],
            TOWN: [MessageHandler(filters.TEXT & ~filters.COMMAND, check_town),
                   CommandHandler('stop', bye)],
            HINT: [MessageHandler(filters.TEXT & ~filters.COMMAND, hint)]
        },
        fallbacks=[CommandHandler('stop', bye)]
    )

    app.add_handler(conv_handler)
    app.add_handler(CommandHandler('dev', dev))
    app.add_handler(CommandHandler('stats', statistics))
    app.add_handler(CommandHandler('help', help_))
    app.add_handler(CommandHandler('status', status))

    app.run_polling()
