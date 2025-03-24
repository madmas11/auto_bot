import asyncio
import email
import imaplib
import logging
import os

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command
from aiogram.types import FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.filters.state import State, StatesGroup
from dotenv import load_dotenv
from email import policy

logging.basicConfig(
    level=logging.INFO,
    filename='logging_bot_work.txt',
    filemode='w'
)

load_dotenv()

BOT_TOKEN = os.getenv('TOKEN_BOT')
PARK_MAIL_LOG = os.getenv('PARK_MAIL_LOGIN')
PARK_MAIL_PASS = os.getenv('PARK_MAIL_PASSWORD')
VORK_MAIL_LOG = os.getenv('VORK_MAIL_LOGIN')
VORK_MAIL_PASS = os.getenv('VORK_MAIL_PASSWORD')
PARK = os.getenv('PARK')
VORK = os.getenv('VORK')
SAVE_DIR = "downloads"
IMAP_SERVERS = {
    "PARK": "imap.yandex.ru",
    "VORK": "imap.mail.ru",
}
SENDERS = {
    "pokazania@komikt.ru": "ККТ",
    "kvit@artic-service.ru": "УГИЦ",
}

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


class PersonState(StatesGroup):
    park_state = State()
    vork_state = State()


if not os.path.exists(SAVE_DIR):
    os.makedirs(SAVE_DIR)


@dp.message(Command('start'))
async def start(message: types.Message):
    await message.answer('Отправь номер лицевого счета и нажми /check')


@dp.message(F.text & ~F.text.startswith('/'))
async def num_score(message: types.Message, state: FSMContext):
    num_check = message.text
    if num_check == PARK:
        await state.set_state(PersonState.park_state)
    elif num_check == VORK:
        await state.set_state(PersonState.vork_state)
    else:
        await message.answer('Неправильный номер')
    return await message.answer('Нажми /check')


@dp.message(Command('check'))
async def check(message: types.Message, state: FSMContext):
    await bot.send_chat_action(chat_id=message.chat.id, action="upload_document")
    user_state = await state.get_state()

    if user_state == PersonState.park_state:
        imap_server = IMAP_SERVERS['PARK']
        mail_log, mail_pass = PARK_MAIL_LOG, PARK_MAIL_PASS

    elif user_state == PersonState.vork_state:
        imap_server = IMAP_SERVERS['VORK']
        mail_log, mail_pass = VORK_MAIL_LOG, VORK_MAIL_PASS

    wait_message = await message.answer("⏳ Пожалуйста, подождите... Идет загрузка файлов.")

    imap = imaplib.IMAP4_SSL(imap_server)
    imap.login(mail_log, mail_pass)
    imap.select('INBOX')

    all_found_files = []
    no_new_messages = True

    for sender, label in SENDERS.items():
        status, messages = imap.search(None, f'(FROM {sender})')
        if status != "OK" or not messages[0]:
            continue

        no_new_messages = False
        latest_email_id = messages[0].split()[-1]
        status, data = imap.fetch(latest_email_id, "(RFC822)")
        if status != "OK":
            await message.answer("❌ Ошибка загрузки письма")
            return

        msg = email.message_from_bytes(data[0][1], policy=policy.default)
        found_files = []
        for part in msg.walk():
            if part.get_content_disposition() == "attachment":
                filename = f'{label}.pdf'
                filepath = os.path.join(SAVE_DIR, filename)

                with open(filepath, "wb") as f:
                    f.write(part.get_payload(decode=True))
                    found_files.append(filepath)
        all_found_files.extend(found_files)

    await bot.delete_message(chat_id=message.chat.id, message_id=wait_message.message_id)

    if no_new_messages:
        await message.answer('Новых квитанций нет')
    if all_found_files:
        for file in all_found_files:
            await bot.send_document(chat_id=message.chat.id, document=FSInputFile(file))


if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
