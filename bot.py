import os
import re
import asyncio
from typing import Optional

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ContentType
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)


# =========================
# ENV
# =========================
TOKEN = os.getenv("TOKEN", "").strip()
ADMIN_CHAT_ID_RAW = os.getenv("ADMIN_CHAT_ID", "").strip()

if not TOKEN:
    raise RuntimeError("TOKEN env yo'q. Koyeb -> Secrets/Environment Variables ga TOKEN qo'shing.")
if not ADMIN_CHAT_ID_RAW:
    raise RuntimeError("ADMIN_CHAT_ID env yo'q. Masalan: 1586199040")

try:
    ADMIN_CHAT_ID = int(ADMIN_CHAT_ID_RAW)
except ValueError:
    raise RuntimeError("ADMIN_CHAT_ID raqam bo'lishi kerak. Masalan: 1586199040")


# =========================
# DATA (yo‘nalishlar / hududlar)
# =========================
DIRECTIONS = [
    "Santexnik",
    "Elektrik",
    "Gaz ustasi",
    "Konditsioner ustasi",
    "Mebel ustasi",
    "Qurilish ustasi(beton,suvoq ishlari)",
    "Kafel ustasi",
    "Bo'yoqchi",
    "Tom ustasi",
    "Svarchik",
    "Maishiy texnika ustasi",
    "Eshik-zamok ustasi",
    "Gipsokarton",
    "Pol ustasi",
    "Plastik/alyumin rom ustasi",
    "Payvandchi",
    "Oddiy ishchi(mardikor)",
    "Boshqa",
]

# Namangan hududlari (tumani qo‘shilgan)
REGIONS = [
    "Namangan shahri",
    "Chortoq tumani",
    "Chust tumani",
    "Kosonsoy tumani",
    "Mingbuloq tumani",
    "Namangan tumani",
    "Norin tumani",
    "Pop tumani",
    "To‘raqo‘rg‘on tumani",
    "Uchqo‘rg‘on tumani",
    "Uychi tumani",
    "Yangiqo‘rg‘on tumani",
]


# =========================
# FSM
# =========================
class Form(StatesGroup):
    menu = State()

    # anketa
    name = State()
    direction = State()
    experience = State()
    services = State()          # ixtiyoriy
    region = State()
    phone = State()
    telegram = State()          # ixtiyoriy
    confirm = State()

    # reklama post
    ad_post = State()


# =========================
# Helpers
# =========================
def profile_link(message_or_user) -> str:
    """
    Username bo'lsa: https://t.me/username
    Bo'lmasa: tg://user?id=123
    """
    u = message_or_user.from_user if hasattr(message_or_user, "from_user") else message_or_user
    if u.username:
        return f"https://t.me/{u.username}"
    return f"tg://user?id={u.id}"


def display_telegram(u) -> str:
    """
    Adminga yuborishda:
    username bo'lsa @username,
    bo'lmasa profil link.
    """
    if u.username:
        return f"@{u.username}"
    return profile_link(u)


def make_inline_kb(items: list[str], prefix: str, cols: int = 2) -> InlineKeyboardMarkup:
    buttons = []
    row = []
    for i, text in enumerate(items, start=1):
        row.append(InlineKeyboardButton(text=text, callback_data=f"{prefix}:{text}"))
        if len(row) == cols:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📝 Anketa to‘ldirish", callback_data="menu:anketa")],
            [InlineKeyboardButton(text="📣 Reklama post yuborish", callback_data="menu:ad")],
        ]
    )


def skip_kb(next_cb: str = "skip") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="⏭️ Keyingisi", callback_data=next_cb)]
        ]
    )


def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup()
        inline_keyboard=[
            [InlineKeyboardButton(text="✅ Tayyor", callback_data="confirm:yes")],
            [InlineKeyboardButton(text="🔁 Qayta to‘ldirish", callback_data="confirm:restart")],
        ]
    def experience_kb() -> InlineKeyboardMarkup:
    # 0-10 yil
    years = [str(i) for i in range(0, 11)]
    return make_inline_kb(years, "exp", cols=3)


def contact_request_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📱 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def normalize_phone(phone: str) -> str:
    phone = phone.strip()
    # +998... bo'lmasa ham, raqamlarni qoldiramiz
    digits = re.sub(r"\D+", "", phone)
    if digits.startswith("998") and not phone.startswith("+"):
        return "+" + digits
    if phone.startswith("+"):
        return phone
    # oxirgi fallback
    return "+" + digits if digits else phone


# =========================
# Bot / DP
# =========================
bot = Bot(
    token=TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
dp = Dispatcher()


# =========================
# START / MENU
# =========================
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await state.set_state(Form.menu)
    text = (
        "👋 Assalomu alaykum!\n\n"
        
        "UstaTop Namangan botiga xush kelibsiz.\n"
        "Bot orqali anketa to‘ldirishingiz yoki reklama postingizni yuborishingiz mumkin.\n\n"
        
        "Kerakli bo‘limni tanlang:"
    )
    await message.answer(text, reply_markup=menu_kb())


@dp.callback_query(F.data.startswith("menu:"))
async def menu_choice(call: CallbackQuery, state: FSMContext):
    choice = call.data.split(":", 1)[1]
    await call.answer()

    if choice == "anketa":
        await state.clear()
        await state.set_state(Form.name)
        await call.message.answer("👤 Ismingizni kiriting:")
        return

    if choice == "ad":
        await state.clear()
        await state.set_state(Form.ad_post)
        await call.message.answer(
            "📣 Reklama postingizni yuboring.\n\n"
            "✅ Matn, rasm, video yoki rasm/video + matn bo‘lishi mumkin.\n"
        )
        return


# =========================
# ANKETA: Name
# =========================
@dp.message(Form.name)
async def form_name(message: Message, state: FSMContext):
    name = message.text.strip() if message.text else ""
    if len(name) < 2:
        await message.answer("❗️ Ism juda qisqa. Qaytadan kiriting:")
        return

    await state.update_data(name=name)
    await state.set_state(Form.direction)
    await message.answer("🛠 Yo‘nalishingizni tanlang:", reply_markup=make_inline_kb(DIRECTIONS, "dir", cols=2))


@dp.callback_query(Form.direction, F.data.startswith("dir:"))
async def form_direction(call: CallbackQuery, state: FSMContext):
    direction = call.data.split(":", 1)[1]
    await call.answer()

    await state.update_data(direction=direction)
    await state.set_state(Form.experience)
    await call.message.answer("🧠 Tajribangizni tanlang (yil):", reply_markup=experience_kb())


@dp.callback_query(Form.experience, F.data.startswith("exp:"))
async def form_experience(call: CallbackQuery, state: FSMContext):
    exp = call.data.split(":", 1)[1]
    await call.answer()

    await state.update_data(experience=exp)
    await state.set_state(Form.services)
    await call.message.answer(
        "🧰 Xizmatlaringiz :\n"
        "Agar yozishni xohlamasangiz, ⏭️ Keyingisi ni bosing.",
        reply_markup=skip_kb("skip:services")
    )


@dp.callback_query(Form.services, F.data == "skip:services")
async def skip_services(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(services="—")
    await state.set_state(Form.region)
    await call.message.answer("📍 Hududingizni tanlang:", reply_markup=make_inline_kb(REGIONS, "reg", cols=2))@dp.message(Form.services)
async def form_services(message: Message, state: FSMContext):
    services = (message.text or "").strip()
    if not services:
        services = "—"
    await state.update_data(services=services)
    await state.set_state(Form.region)
    await message.answer("📍 Hududingizni tanlang:", reply_markup=make_inline_kb(REGIONS, "reg", cols=2))


@dp.callback_query(Form.region, F.data.startswith("reg:"))
async def form_region(call: CallbackQuery, state: FSMContext):
    region = call.data.split(":", 1)[1]
    await call.answer()

    await state.update_data(region=region)
    await state.set_state(Form.phone)

    # Telefon uchun request_contact - bu faqat ReplyKeyboard
    await call.message.answer(
        "📞 Telefon raqamingizni yuboring.\n\n"
        "👇 Pastdagi tugmani bosib yuboring (avtomatik yuboradi).",
        reply_markup=contact_request_kb()
    )


@dp.message(Form.phone, F.contact)
async def form_phone_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number if message.contact else ""
    phone = normalize_phone(phone)

    await state.update_data(phone=phone)
    await state.set_state(Form.telegram)

    await message.answer("✅ Qabul qilindi.", reply_markup=ReplyKeyboardRemove())
    await message.answer(
        "💬 Telegram username’ingizni yuboring (masalan: @username).\n"
        "Agar username bo‘lmasa yoki yubormoqchi bo‘lmasangiz, ⏭️ Keyingisi ni bosing.\n\n",
        reply_markup=skip_kb("skip:telegram")
    )


@dp.message(Form.phone)
async def form_phone_text_fallback(message: Message, state: FSMContext):
    # Agar user contact yubormasa, qo'lda raqam yozsa ham qabul qilamiz
    phone = (message.text or "").strip()
    if not phone or len(re.sub(r"\D+", "", phone)) < 7:
        await message.answer("❗️ Telefon raqam noto‘g‘ri. Pastdagi tugma bilan yuboring 👇", reply_markup=contact_request_kb())
        return

    await state.update_data(phone=normalize_phone(phone))
    await state.set_state(Form.telegram)
    await message.answer("✅ Qabul qilindi.", reply_markup=ReplyKeyboardRemove())
    await message.answer(
        "💬 Telegram username’ingizni yuboring (masalan: @username).\n"
        "Agar username bo‘lmasa, ⏭️ Keyingisi ni bosing.",
        reply_markup=skip_kb("skip:telegram")
    )


@dp.callback_query(Form.telegram, F.data == "skip:telegram")
async def skip_telegram(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.update_data(telegram="—")
    await state.set_state(Form.confirm)
    await send_summary(call.message, state)


@dp.message(Form.telegram)
async def form_telegram(message: Message, state: FSMContext):
    tg = (message.text or "").strip()
    if tg and not tg.startswith("@"):
        # odam "username" deb yozsa ham @ qo'shib qo'yamiz
        if re.fullmatch(r"[A-Za-z0-9_]{5,32}", tg):
            tg = "@" + tg

    # agar noto‘g‘ri bo‘lsa ham userni qiynamaymiz, ixtiyoriy edi
    if not tg:
        tg = "—"

    await state.update_data(telegram=tg)
    await state.set_state(Form.confirm)
    await send_summary(message, state)


async def send_summary(message: Message, state: FSMContext):
    data = await state.get_data()
    u = message.from_user

    # telegram ko'rsatish: agar user username bo'lmasa profil link
    tg_display = data.get("telegram", "—")
    if tg_display == "—":
        tg_display = display_telegram(u)

    text = (
        "🧾 <b>Anketa ma’lumotlari</b>\n\n"
        f"👤 <b>Ism:</b> {data.get('name')}\n"
        f"🛠 <b>Yo‘nalish:</b> {data.get('direction')}\n"
        f"🧠 <b>Tajriba:</b> {data.get('experience')}\n"
        f"🧰 <b>Xizmatlar:</b> {data.get('services')}\n"
        f"📍 <b>Hudud:</b> {data.get('region')}\n"
        f"📞 <b>Telefon:</b> {data.get('phone')}\n"
        f"💬 <b>Telegram:</b> {tg_display}\n\n"
        "✅ Hammasi to‘g‘rimi? Unda <b>✅ Tayyor</b> ni bosing."
    )
    await message.answer(text, reply_markup=confirm_kb())@dp.callback_query(Form.confirm, F.data.startswith("confirm:"))
async def form_confirm(call: CallbackQuery, state: FSMContext):
    action = call.data.split(":", 1)[1]
    await call.answer()

    if action == "restart":
        await state.clear()
        await state.set_state(Form.name)
        await call.message.answer("🔁 Qayta boshlaymiz.\n\n👤 Ismingizni kiriting:")
        return

    # confirm yes
    data = await state.get_data()
    u = call.from_user

    # Admin xabarida "Kimdan" faqat profil link bo‘lsin (username emas)
    sender_profile = profile_link(u)

    # Telegram satri: user yuborgan bo'lsa o'sha, bo'lmasa profil link
    tg_line = data.get("telegram", "—")
    if tg_line == "—":
        tg_line = sender_profile if not u.username else f"https://t.me/{u.username}"

    admin_text = (
        "🆕 <b>Yangi anketa ✅</b>\n\n"
        f"👤 <b>Kimdan:</b> {sender_profile}\n\n"
        f"🧑‍🔧 <b>Ism:</b> {data.get('name')}\n"
        f"🛠 <b>Yo‘nalish:</b> {data.get('direction')}\n"
        f"🧠 <b>Tajriba:</b> {data.get('experience')}\n"
        f"🧰 <b>Xizmatlar:</b> {data.get('services')}\n"
        f"📍 <b>Hudud:</b> {data.get('region')}\n"
        f"📞 <b>Telefon:</b> {data.get('phone')}\n"
        f"💬 <b>Telegram:</b> {tg_line}\n"
    )

    await bot.send_message(ADMIN_CHAT_ID, admin_text)

    await state.set_state(Form.menu)
    await call.message.answer(
        "✅ Anketangiz qabul qilindi.\nTez orada kanalga joylanadi. Rahmat!",
        reply_markup=menu_kb()
    )


# =========================
# REKLAMA POST
# =========================
@dp.message(Form.ad_post)
async def ad_post_receive(message: Message, state: FSMContext):
    """
    User rasm/video/text yuborsa:
    - O'zi forward qilamiz (caption saqlanadi)
    - Admin ga alohida "kimdan" profil link bilan xabar yuboramiz
    """
    u = message.from_user
    sender_profile = profile_link(u)

    # 1) Adminga kimdanligi
    await bot.send_message(
        ADMIN_CHAT_ID,
        f"📣 <b>Yangi reklama post ✅</b>\n👤 <b>Kimdan:</b> {sender_profile}"
    )

    # 2) Postni forward qilish (caption ham ketadi)
    try:
        await bot.forward_message(
            chat_id=ADMIN_CHAT_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
    except Exception:
        # Forward bo'lmasa, minimal copy qilamiz
        if message.content_type == ContentType.TEXT:
            await bot.send_message(ADMIN_CHAT_ID, message.text)
        else:
            await bot.send_message(ADMIN_CHAT_ID, "❗️ Postni forward qilishda xatolik bo‘ldi (copy qilib bo‘lmadi).")

    await state.set_state(Form.menu)
    await message.answer(
        "✅ Qabul qilindi.\nReklama postingiz adminga yuborildi. Rahmat!",
        reply_markup=menu_kb()
    )


# =========================
# Run
# =========================
async def main():
    await dp.start_polling(bot)


if name == "main":
    asyncio.run(main())
