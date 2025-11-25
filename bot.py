import asyncio
import logging
import os
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, Router, types, F
from aiogram.filters import Command
from aiogram.types import Message

# ================= НАСТРОЙКИ =================
API_TOKEN = os.getenv('API_TOKEN')  # ← сюда токен от @BotFather

# Время в секундах = 24 часа
RESPAWN_TIME = 24 * 60 * 60

# =============================================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()

# Словарь: chat_id → время последнего сообщения "1"/"2"/"3"
last_signal_time = {}

# Словарь: chat_id → задача, которая должна отправить «Ак респ»
scheduled_tasks = {}


async def schedule_respawn(message: Message):
    chat_id = message.chat.id

    # Отменяем старую задачу, если была
    if chat_id in scheduled_tasks and not scheduled_tasks[chat_id].cancelled():
        scheduled_tasks[chat_id].cancel()

    # Запоминаем время
    last_signal_time[chat_id] = datetime.now()

    # Создаём новую задачу через 24 часа
    task = asyncio.create_task(wait_and_send_respawn(chat_id))
    scheduled_tasks[chat_id] = task


async def wait_and_send_respawn(chat_id: int):
    await asyncio.sleep(RESPAWN_TIME)

    # Проверяем, не было ли новых сигналов за это время
    if chat_id in last_signal_time:
        last_time = last_signal_time[chat_id]
        if datetime.now() - last_time >= timedelta(seconds=RESPAWN_TIME - 5):  # ±5 сек на погрешность
            try:
                await bot.send_message(chat_id, "Ак респ")
            except Exception as e:
                print(f"Не смог отправить в {chat_id}: {e}")

    # Удаляем из словарей
    last_signal_time.pop(chat_id, None)
    scheduled_tasks.pop(chat_id, None)


@router.message(F.text.in_({"1", "2", "3"}))
async def on_signal(message: Message):
    # Если кто-то написал 1/2/3 вручную — тоже реагируем
    if message.from_user.is_bot:
        return

    await message.reply("Засёк сигнал! Жду 24 часа…")

    await schedule_respawn(message)


# Опционально: команда /status — посмотреть, сколько осталось до респа
@router.message(Command("status"))
async def cmd_status(message: Message):
    chat_id = message.chat.id
    if chat_id not in last_signal_time:
        await message.reply("Пока нет активного таймера.")
        return

    remaining = RESPAWN_TIME - (datetime.now() - last_signal_time[chat_id]).total_seconds()
    if remaining <= 0:
        await message.reply("Таймер уже должен был сработать (возможно, бот был выключен).")
    else:
        hours = int(remaining // 3600)
        minutes = int((remaining % 3600) // 60)
        await message.reply(f"До «Ак респ» осталось: {hours} ч {minutes} мин")


async def main():
    dp.include_router(router)
    # Удаляем вебхуки (на случай, если бот раньше работал на другом хостинге)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())