"""
записки сумасшедшего:
тг бот weirdo. с ним можно играть в угадайку. а ещё он кричит на вас.
"""
import telebot
from telebot import types
from telebot.util import update_types
from telebot.handler_backends import State, StatesGroup
from random import randint
import time as tm
from telebot import apihelper

# для антиспама
apihelper.ENABLE_MIDDLEWARE = True

# токен не берите мой пожалуйста (записан в эскейп-символах utf-8 (умнеес ничего не придумал))
bot = telebot.TeleBot(
    """\x36\x34\x33\x37\x30\x36\x35\x37\x32\x32\x3a\x41\x41\x47\x35\x52\x38\x6e\x53\x75\x72\x55\x64\x47\x4f\x41\x48\x77\x34\x42\x32\x41\x4d\x78\x6c\x46\x61\x6d\x63\x35\x4c\x71\x61\x51\x6f\x63"""
)

# я знаю, что это отвратительная практика.  
# никак иначе не могу.  
# sql, скорее всего, не оптимальное решение.  
# редис надо устанавливать.  
# ну а тогда просто сделаем так.  
notes = {}

LOW_BOUND_GUESS = -1024
HIGH_BOUND_GUESS = 1024
TRIES_AMOUNT = 10
GUESSING_STATE = 'guessing'
IDLE_STATE = 'idle'
RULES_GUESSING = f"""игра угадайка. 
угадайте целое число в интервале [{LOW_BOUND_GUESS}; {HIGH_BOUND_GUESS}].
даётся 10 попыток.
ответ даётся в формате "больше-меньше загаданного".
вводятся десятичные числа. целые. ни hexadecimal, ни двоичные числа, ни римские и прочее. десятичные.
несоблюдение правил наказуемо.
не угадаете за кол-во попыток - ваш компьютер взорвётся (шутка).
есть случайность. это как сапёр (снова шутка кстати).
"""
END_GUESSING_FAIL = f"конец игры хаха вы не смогли перебрать {HIGH_BOUND_GUESS - LOW_BOUND_GUESS} чисел за {TRIES_AMOUNT} ходов"
END_GUESSING_SUCCESS = "бинарный поиск ;) ;) ;) бип буп"
GUESS_LESSER_THAN_SECRET = "<"
GUESS_GREATER_THAN_SECRET = ">"

spams = {}
MAX_MSG_AMOUNT = 4  # Messages in
TIMEOUT = 5  # Seconds
BAN = 300  # Seconds

keyboard = types.InlineKeyboardMarkup()
keyboard.add(types.InlineKeyboardButton("покричать", callback_data="scream"))
keyboard.add(types.InlineKeyboardButton("угадайка", callback_data="guess"))


# честно скопировано с хабра
def is_spam(user_id):
    try:
        usr = spams[user_id]
        usr["messages"] += 1
    except:
        spams[user_id] = {"next_time": int(tm.time()) + TIMEOUT, "messages": 1, "banned": 0}
        usr = spams[user_id]
    if usr["banned"] >= int(tm.time()):
        return True
    else:
        if usr["next_time"] >= int(tm.time()):
            if usr["messages"] >= MAX_MSG_AMOUNT:
                spams[user_id]["banned"] = tm.time() + BAN
                return True
        else:
            spams[user_id]["messages"] = 1
            spams[user_id]["next_time"] = int(tm.time()) + TIMEOUT
    return False


@bot.middleware_handler(update_types=['message', 'inline_query'])
def antispam(bot_instance, update):
    is_spam(update.chat.id)


@bot.callback_query_handler(func=lambda call: True)
# не понял что за лямбда это если честно.
# ну и на деле это не особо интересно скорее всего.
def callback(call):
    if call.message:
        if call.data == 'scream':
            scream(call.message)
        if call.data == 'guess':
            start_guess(call.message)


@bot.message_handler(regexp='(^-?[1-9]\d*$)|(^0$)')
def reply_to_guess(message):
    if f"{message.chat.id}_state" in notes.keys():
        if (notes[f"{message.chat.id}_state"] == GUESSING_STATE):
            notes[f"{message.chat.id}_tries"] -= 1
            if (notes[f"{message.chat.id}_tries"] < 0):
                bot.send_message(message.chat.id, END_GUESSING_FAIL, reply_markup=keyboard)
                notes[f"{message.chat.id}_state"] = IDLE_STATE
                return

            guess = try_convert_str_to_int(message.text)
            if (guess[0]):
                guess = guess[1]
            else:
                bot.send_message(message.chat.id, "не то чёто отправили вы мне")
                return

            secret = notes[f"{message.chat.id}_secret"]
            answer = ''
            if abs(guess) > HIGH_BOUND_GUESS:
                bot.send_message("ну как вы сами думаете, > или < ?")
                return

            if guess == secret:
                bot.send_message(message.chat.id, END_GUESSING_SUCCESS)

            if guess < secret:
                answer += f'{GUESS_LESSER_THAN_SECRET}\n'

            if guess > secret:
                answer += f'{GUESS_GREATER_THAN_SECRET}\n'
            tries = notes[f"{message.chat.id}_tries"]
            bot.send_message(message.chat.id, f"{answer}\nкол-во попыток осталось: {tries}")


@bot.message_handler(regexp='^-0$')
def smart_one(message):
    bot.send_message(message.chat.id, 'какие мы умные да')
    if f"{message.chat.id}_state" in notes.keys():
        if (notes[f"{message.chat.id}_state"] == GUESSING_STATE):
            notes[f"{message.chat.id}_tries"] -= 4
        if (notes[f"{message.chat.id}_tries"] < 0):
            tm.sleep(1)
            notes[f"{message.chat.id}_state"] = IDLE_STATE
            bot.send_message(message.chat.id, 'а вот зря умничали. вы проиграли', reply_markup=keyboard)


@bot.message_handler(commands=['start'])
def start(message):
    notes[f"{message.chat.id}_state"] = IDLE_STATE

    bot.send_message(message.chat.id, 'привте', reply_markup=keyboard)


def start_guess(message):
    if f"{message.chat.id}_state" in notes.keys():
        if (notes[f"{message.chat.id}_state"] == 'idle'):
            # пишем секрет, кол-во попыток и состояние в словарь
            notes[f"{message.chat.id}_secret"] = randint(
                LOW_BOUND_GUESS, HIGH_BOUND_GUESS)
            notes[f"{message.chat.id}_tries"] = TRIES_AMOUNT
            notes[f"{message.chat.id}_state"] = GUESSING_STATE
            bot.send_message(chat_id=message.chat.id, text=RULES_GUESSING)


def scream(message):
    scream_length = randint(0, 90)
    scream_line = 'AAAAAAAAAA'
    for i in range(scream_length):
        scream_line += 'A'
    bot.send_message(chat_id=message.chat.id, text=scream_line, reply_markup=keyboard)


def try_convert_str_to_int(line: str) -> tuple:
    try:
        return True, int(line, base=10)
    except ValueError:
        return False,


if __name__ == "__main__":
    bot.set_my_commands([telebot.types.BotCommand('start', 'начать приколы')])
    bot.infinity_polling()