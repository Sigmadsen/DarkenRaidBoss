import asyncio
import logging
import os
from datetime import datetime

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import Command
from aiogram.types import Message

# ================= НАСТРОЙКИ =================
API_TOKEN = os.getenv('API_TOKEN')
if not API_TOKEN:
    raise ValueError("Не найден API_TOKEN в переменных окружения!")

TIME_TO_MAYBE_ALIVE = 24 * 3600   # 24 часа — предупреждение
TIME_TO_EXACT_RESPAWN = 26 * 3600  # 26 часов — точный респ (24 + 2)
# =============================================

logging.basicConfig(level=logging.INFO)

bot = Bot(token=API_TOKEN)
dp = Dispatcher()
router = Router()

# chat_id → время убийства АКа
kill_time_db = {}

# задачи (на 24ч и 26ч)
task_warn = {}
task_respawn = {}


async def start_timers(chat_id: int, kill_time: datetime):
    # отменяем старые
    for t in [task_warn.get(chat_id), task_respawn.get(chat_id)]:
        if t and not t.cancelled():
            t.cancel()

    # через 24ч — предупреждение
    task_warn[chat_id] = asyncio.create_task(warn_maybe_alive(chat_id, kill_time))
    # через 26ч — точный респ
    task_respawn[chat_id] = asyncio.create_task(send_exact_respawn(chat_id, kill_time))


async def warn_maybe_alive(chat_id: int, original_kill_time: datetime):
    await asyncio.sleep(TIME_TO_MAYBE_ALIVE)
    if chat_id in kill_time_db and kill_time_db[chat_id] == original_kill_time:
        await bot.send_message(
            chat_id,
            "Ак может быть жив прямо сейчас!\nРесп через 0–2 часа"
        )


async def send_exact_respawn(chat_id: int, original_kill_time: datetime):
    await asyncio.sleep(TIME_TO_EXACT_RESPAWN)
    if chat_id in kill_time_db and kill_time_db[chat_id] == original_kill_time:
        await bot.send_message(chat_id, "Ак респ")

        # чистим после точного респа
        kill_time_db.pop(chat_id, None)
        task_warn.pop(chat_id, None)
        task_respawn.pop(chat_id, None)


@router.message(F.text.in_({"АК убит", "Ак убит", "ак убит"}))
async def on_kill(message: Message):
    # Если кто-то написал 1/2/3 вручную — тоже реагируем
    if message.from_user.is_bot:
        return

    chat_id = message.chat.id
    now = datetime.now()

    kill_time_db[chat_id] = now
    await message.reply("Таймер АКа запущен!\nТочный респ через 24 + (от 0 до 2х) часов.")

    await start_timers(chat_id, now)


@router.message(Command("status"))
async def cmd_status(message: Message):
    chat_id = message.chat.id

    if chat_id not in kill_time_db:
        await message.reply("Таймер не запущен.")
        return

    elapsed = (datetime.now() - kill_time_db[chat_id]).total_seconds()
    remaining = TIME_TO_EXACT_RESPAWN - elapsed

    if remaining <= 0:
        await message.reply("Ак уже должен быть заспавнен!")
        return

    hours = int(remaining // 3600)
    minutes = int((remaining % 3600) // 60)

    status_text = f"До точного респа АКа осталось:\n{hours} ч {minutes} мин"

    # бонусом показываем, прошло ли уже 24 часа
    if elapsed >= TIME_TO_MAYBE_ALIVE:
        status_text += "\n\nАк уже может быть жив!"

    await message.reply(status_text)


async def main():
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())