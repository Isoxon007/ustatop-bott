import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import ReplyKeyboardMarkup, KeyboardButton
from aiogram.filters import CommandStart

TOKEN = "BU_YERGA_BOT_TOKENINGNI_QOY"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# MENU
menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📝 Anketa to‘ldirish")],
        [KeyboardButton(text="📢 Reklama post yuborish")]
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def start(message: types.Message):
    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "UstaTop Namangan botiga xush kelibsiz.\n"
        "Bot orqali anketa to‘ldirishingiz yoki reklama postingizni yuborishingiz mumkin.\n\n"
        "Kerakli bo‘limni tanlang:",
        reply_markup=menu
    )

@dp.message(F.text == "📝 Anketa to‘ldirish")
async def anketa(message: types.Message):
    await message.answer("👤 Ismingizni kiriting:")

@dp.message(F.text == "📢 Reklama post yuborish")
async def reklama(message: types.Message):
    await message.answer("📎 Reklama postingizni yuboring (rasm/video + matn).")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
