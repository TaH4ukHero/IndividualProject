import json
import requests
from bs4 import BeautifulSoup
from telegram import ReplyKeyboardMarkup
# from dotenv import dotenv_values FOR Glitch
from data.db_session import create_session
from data.users import User

towns_exceptions = ["Йошкар-Ола", 'Каменск-Уральский', 'Комсомольск-на-Амуре', 'Орехово-Зуево',
                    'Петропавловск-Камчатский', 'Ростов-на-Дону', 'Санкт-Петербург', 'Улан-Удэ',
                    'Ханты-Мансийск', 'Южно-Сахалинск']


def print_guessed_letters(context):
    letters = context.user_data["guessed_letters"]
    guessed_town = context.user_data["guessed_town"]
    out = []
    for val in guessed_town:
        if val.lower() in letters:
            out += guessed_town[guessed_town.index(val)]
            guessed_town = list(''.join(guessed_town).replace(val, '*', 1))
        elif val == ' ' or val == '-':
            out += ' '
        else:
            out += '_'
    if ' ' in out:
        return ' '.join([i.capitalize() for i in ''.join(out).split(' ')])
    return out


def get_desc_of_town(town):
    with open('Cyrillic2Latin.json', encoding='utf8') as f:
        if '-' in town and town not in towns_exceptions:
            Latin_town = json.load(f).get(' '.join([i.capitalize() for i in town.split('-')]))
        else:
            if len(town.split(' ')) > 1 and town.split(' ')[1]:
                town = ' '.join([i.capitalize() for i in town.split(' ')])
            Latin_town = json.load(f).get(town)
        url = f"https://wikiway.com/russia/{Latin_town.lower().replace(' ', '-')}/"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/112.0.0.0 Safari/537.36"}
    r = requests.get(url=url, headers=headers)
    if r.status_code != 200:
        main_moments = 'К сожалению статьи не будет'
        return [main_moments, url]
    soup = BeautifulSoup(r.content, 'lxml')
    main_moments = soup.find(class_='element-publ').find('p').text
    return [main_moments, url]


def few_facts_abt_town(town, mode=False):
    if '-' in town and town not in towns_exceptions:
        town = ' '.join([i.capitalize() for i in town.split('-')])
    elif len(town.split(' ')) > 1 and town.split(' ')[1]:
        town = ' '.join([i.capitalize() for i in town.split(' ')])
    out = ''
    out += f'Название - <b>{town}</b>\n'
    with open('town2population.json', encoding='utf8') as file:
        population = json.load(file).get(town)
        out += f"Население - <b>{population}</b> человек\n"
    with open('town2AdmArea.json', encoding='utf8') as f:
        admArea = json.load(f).get(town)
    if mode:
        return admArea
    out += f'Административный округ - <b>{admArea}</b>\n'
    main_moments, url = get_desc_of_town(town)
    if main_moments != 'К сожалению статьи не будет':
        out += f'\n<b>Немного о городе</b>\n\n{main_moments}\n\n'
        out += f'Больше можно узнать по ссылке <b>{url}</b>'
    return out


def win(context):
    keyboard = ReplyKeyboardMarkup([['ДА', 'НЕТ']], resize_keyboard=True, one_time_keyboard=True)
    msg1 = f'<b>Молодец! Ты угадал!\nХочешь сыграть еще раз?</b>'
    msg2 = few_facts_abt_town(''.join(context.user_data["guessed_town"]))
    return [keyboard, msg1, msg2]


def hint_2(msg, user_data, mode='letter'):
    if mode == 'adm_area':
        return [few_facts_abt_town(user_data["guessed_town"], mode=True), user_data]
    while msg.lower() in user_data["not_guessed_letters"] or msg in user_data["not_guessed_letters"]:
        if msg.lower() in user_data["not_guessed_letters"]:
            user_data["not_guessed_letters"].remove(msg.lower())
        if msg in user_data["not_guessed_letters"]:
            user_data["not_guessed_letters"].remove(msg)
    return user_data


def fix_results(update, context, result: str) -> None:
    sess = create_session()  # Создание сессии с ДБ
    user = sess.query(User).filter(User.user_id == update.effective_user.id).first()  # Поиск Юзера
    if user is None:  # Если юзера не существует, то добавляем
        user = User()
        user.user_id = update.effective_user.id
        sess.add(user)
        sess.commit()
        user = sess.query(User).filter(User.user_id == update.effective_user.id).first()
    if result == 'WIN':
        user.wins = user.wins + 1
    elif result == 'LOSE':
        user.loses += 1
    if context.user_data.get('attempts', 0) != 0:
        user.last_attempts = context.user_data['attempts']
        if user.min_attempts > 0:
            user.min_attempts = min(user.min_attempts, context.user_data['attempts'])
        else:
            user.min_attempts = context.user_data['attempts']
        user.most_attempts = max(user.most_attempts, context.user_data['attempts'])
        user.attempts += context.user_data['attempts']
    sess.commit()
    context.user_data.clear()  # Удаление информации об игре с пользователем

