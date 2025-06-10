import os
import tempfile
import telebot
from telebot import types
from googletrans import Translator, LANGUAGES
from faster_whisper import WhisperModel
from pydub import AudioSegment

TOKEN = "ТОКЕН"
bot = telebot.TeleBot(TOKEN)
translator = Translator()
model = WhisperModel("small", device="cpu", compute_type="int8")

# Храним состояние пользователей
user_state = {}  # chat_id: {"active": True, "lang": "ru"}

def get_user_state(chat_id):
    if chat_id not in user_state:
        user_state[chat_id] = {"active": True, "lang": "ru"}
    return user_state[chat_id]

def convert_ogg_to_wav(ogg_path, wav_path):
    audio = AudioSegment.from_file(ogg_path)
    audio.export(wav_path, format="wav")

@bot.message_handler(commands=['start'])
def start_handler(message):
    state = get_user_state(message.chat.id)
    state["active"] = True
    bot.send_message(message.chat.id, f"✅ Перевод включён. Текущий язык: {state['lang']}.")

@bot.message_handler(commands=['stop'])
def stop_handler(message):
    state = get_user_state(message.chat.id)
    state["active"] = False
    bot.send_message(message.chat.id, "⛔ Перевод отключён. Чтобы снова включить — /start.")

@bot.message_handler(commands=['lang'])
def lang_handler(message):
    parts = message.text.strip().split()
    if len(parts) != 2:
        bot.send_message(message.chat.id, "❗ Использование: /lang <код_языка> (например, /lang en, /lang de)")
        return

    lang_code = parts[1].lower()
    if lang_code not in LANGUAGES:
        bot.send_message(
            message.chat.id,
            f"❌ Неверный код языка: {lang_code}\n✅ Пример: /lang en (английский), /lang ru (русский), /lang de (немецкий)"
        )
        return

    state = get_user_state(message.chat.id)
    state["lang"] = lang_code
    lang_name = LANGUAGES[lang_code].capitalize()
    bot.send_message(message.chat.id, f"✅ Язык перевода установлен: {lang_name} ({lang_code})")

@bot.message_handler(commands=['help'])
def help_handler(message):
    help_text = (
        "🤖 Команды бота:\n"
        "/start — включить перевод\n"
        "/stop — выключить перевод\n"
        "/lang <код_языка> — сменить язык перевода (например, /lang en)\n"
        "/help — справка\n\n"
        "🎤 Отправь голосовое или текст — я распознаю и переведу!"
    )
    bot.send_message(message.chat.id, help_text)

@bot.message_handler(content_types=['voice'])
def voice_handler(message):
    state = get_user_state(message.chat.id)
    if not state["active"]:
        return

    bot.send_chat_action(message.chat.id, "typing")
    file_info = bot.get_file(message.voice.file_id)
    downloaded_file = bot.download_file(file_info.file_path)

    with tempfile.NamedTemporaryFile(suffix=".ogg", delete=False) as ogg_file:
        ogg_file.write(downloaded_file)
        ogg_path = ogg_file.name

    wav_path = ogg_path.replace(".ogg", ".wav")
    convert_ogg_to_wav(ogg_path, wav_path)

    segments, _ = model.transcribe(wav_path)
    text = " ".join([seg.text for seg in segments])

    os.remove(ogg_path)
    os.remove(wav_path)

    bot.send_message(message.chat.id, f"🗣 Распознано:\n{text.strip()}")

    translated = translator.translate(text.strip(), dest=state["lang"]).text
    bot.send_message(message.chat.id, f"🔤 Перевод ({state['lang']}):\n{translated}")

@bot.message_handler(func=lambda m: True)
def text_handler(message):
    state = get_user_state(message.chat.id)
    if not state["active"]:
        return

    translated = translator.translate(message.text, dest=state["lang"]).text
    bot.send_message(message.chat.id, f"🔤 Перевод ({state['lang']}):\n{translated}")

if __name__ == "__main__":
    bot.polling()
