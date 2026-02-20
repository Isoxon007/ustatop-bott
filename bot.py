import os
import re
import html
import asyncio
from typing import List, Optional

from aiogram import Bot, Dispatcher, Router, F
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.storage.memory import MemoryStorage


# =========================
#   ENV sozlamalar
# =========================
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi. Environment variables ga BOT_TOKEN qo'ying.")
if ADMIN_ID == 0:
    raise RuntimeError("ADMIN_ID topilmadi. Environment variables ga ADMIN_ID (son) qo'ying.")


# =========================
#   Bot / Dispatcher
# =========================
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())
router = Router()
dp.include_router(router)


# =========================
#   States
# =========================
class Form(StatesGroup):
    name = State()
    direction = State()
    experience = State()

    services = State()   # ixtiyoriy
    
    region = State()
    phone = State()
    work_media = State() # ixtiyoriy ish rasmlari/video
    confirm = State()

class AdPost(StatesGroup):
    waiting_post = State()


# =========================
#   Data ro'yxatlar
# =========================
DIRECTIONS = [
    "Santexnik",
    "Elektrik",
    "Gaz ustasi",
    "Konditsioner ustasi",
    "Mebel ustasi",
    "Qurilish ustasi(beton,suvoq ishlari",
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
    "Oddiy ishchi(mardikor",
]

# Namangan tumanlari (hammasi "tumani" bilan)
REGIONS = [
    "Namangan shahri",
    "Chortoq tumani",
    "Chust tumani",
    "Kosonsoy tumani",
    "Mingbuloq tumani",
    "Namangan tumani",
    "Norin tumani",
    "Pop tumani",
    "To'raqo'rg'on tumani",
    "Uchqo'rg'on tumani",
    "Uychi tumani",
    "Yangiqo'rg'on tumani",
]


# =========================
#   Klaviaturalar
# =========================
def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Anketa to'ldirish", callback_data="menu:form")],
        [InlineKeyboardButton(text="📢 Reklama post yuborish", callback_data="menu:ad")],
    ])

def directions_kb() -> InlineKeyboardMarkup:
    rows = []
    for d in DIRECTIONS:
        rows.append([InlineKeyboardButton(text=d, callback_data=f"dir:{d}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def exp_kb() -> InlineKeyboardMarkup:
    # 1-10 yil + 10+ yil
    rows = []
    for i in range(1, 11):
        rows.append([InlineKeyboardButton(text=f"{i} yil", callback_data=f"exp:{i}")])
    rows.append([InlineKeyboardButton(text="10+ yil", callback_data="exp:10+")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def regions_kb() -> InlineKeyboardMarkup:
    rows = []
    for r in REGIONS:
        rows.append([InlineKeyboardButton(text=r, callback_data=f"reg:{r}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def skip_kb(next_cb: str = "skip") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Keyingisi", callback_data=next_cb)]
    ])

def media_done_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tugatdim", callback_data="media:done")],
        [InlineKeyboardButton(text="➡️ O'tkazib yuborish", callback_data="media:skip")],
    ])

def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="confirm:yes")],
        [InlineKeyboardButton(text="🔄 Qayta to'ldirish", callback_data="confirm:restart")],
        [InlineKeyboardButton(text="🏠 Menyu", callback_data="confirm:menu")],
    ])

def phone_request_kb() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="📲 Telefon raqamni yuborish", request_contact=True)]],
        resize_keyboard=True,
        one_time_keyboard=True
    )


# =========================
#   Yordamchi funksiyalar
# =========================
def escape(s: str) -> str:
    return html.escape(s or "")

def build_profile_html(user) -> str:
    """
    Username bo'lsa @username,
    bo'lmasa tg://user?id=... orqali profil link
    """
    if user.username:
        return f"@{escape(user.username)}"
    # HTML link
    return f'<a href="tg://user?id={user.id}">Profil</a>'

def normalize_phone(phone: str) -> str:
    # Eng sodda normalize: faqat raqam va + qoldiramiz
    p = phone.strip()
    p = re.sub(r"[^\d+]", "", p)
    return p

async def send_admin_summary(state: FSMContext, user: Message | CallbackQuery):
    data = await state.get_data()

    # user info
    if isinstance(user, Message):
        u = user.from_user
    else:
        u = user.from_user

    full_name = escape(u.full_name or "")
    user_id = u.id
    profile = build_profile_html(u)

    name = escape(data.get("name", "—"))
    direction = escape(data.get("direction", "—"))
    exp = escape(str(data.get("experience", "—")))
    region = escape(data.get("region", "—"))
    phone = escape(data.get("phone", "—"))
    services = escape(data.get("services", "—"))

    txt = (
        "🆕 <b>Yangi anketa</b> ✅\n\n"
        f"👤 <b>Kimdan:</b> {full_name} | ID: <code>{user_id}</code>\n"
        f"🔗 <b>Profil:</b> {profile}\n\n"
        f"🧑‍🔧 <b>Ism:</b> {name}\n"
        f"🛠 <b>Yo‘nalish:</b> {direction}\n"
        f"🧠 <b>Tajriba:</b> {exp}\n"
        
        f"🧰 <b>Xizmatlar:</b> {services}\n"
        
        f"📍 <b>Hudud:</b> {region}\n"
        f"📞 <b>Telefon:</b> {phone}\n"
    )

    await bot.send_message(chat_id=ADMIN_ID, text=txt, parse_mode="HTML")

    # Ish rasmlari/video bo'lsa - admin ga alohida yuboramiz
    media_list: List[dict] = data.get("work_media_list", [])
    if media_list:
        await bot.send_message(
            chat_id=ADMIN_ID,
            text="🖼 <b>Ish rasmlari / videolar:</b>",
            parse_mode="HTML"
        )
        for item in media_list[:10]:  # limit: 10 ta
            mtype = item.get("type")
            file_id = item.get("file_id")
            caption = item.get("caption", "")
            cap = (f"Ish namunasi\n{caption}".strip()) if caption else "Ish namunasi"

            try:
                if mtype == "photo":
                    await bot.send_photo(ADMIN_ID, photo=file_id, caption=cap)
                elif mtype == "video":
                    await bot.send_video(ADMIN_ID, video=file_id, caption=cap)
                else:
                    # fallback
                    await bot.send_message(ADMIN_ID, f"Media: {file_id}")
            except Exception:
                await bot.send_message(ADMIN_ID, "❗ Media yuborishda xatolik bo'ldi (file_id).")


# =========================
#   START
# =========================
@router.message(CommandStart())
async def start_cmd(message: Message, state: FSMContext):
    await state.clear()
    text = (
        "👋 Assalomu alaykum!\n\n"
        
        "UstaTop Namangan botiga xush kelibsiz.\n"
        "Bot orqali anketa to‘ldirishingiz yoki reklama postingizni yuborishingiz mumkin.\n\n"
        
        "Kerakli bo‘limni tanlang:"
    )
    await message.answer(text, reply_markup=main_menu_kb())


@router.callback_query(F.data == "menu:form")
async def menu_form(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.clear()
    await state.set_state(Form.name)

    # Telegram profil qiymatini boshidan avtomatik tayyorlab qo'yamiz
    telegram_profile = build_profile_html(cb.from_user)
    await state.update_data(telegram=telegram_profile)

    await cb.message.answer("🧑‍🔧 Ismingizni kiriting:")


@router.callback_query(F.data == "menu:ad")
async def menu_ad(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.clear()
    await state.set_state(AdPost.waiting_post)

    await cb.message.answer(
        "📢 Reklama postingizni yuboring (rasm/video + matni bilan yuboring).\n\n"
        "✅ Siz yuborgan post admin tomonidan ko‘rib chiqiladi.",
        reply_markup=skip_kb("ad:cancel")
    )


@router.callback_query(F.data == "ad:cancel")
async def ad_cancel(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.clear()
    await cb.message.answer("🏠 Menyu:", reply_markup=main_menu_kb())


# =========================
#   ANKETA: Ism
# =========================
@router.message(Form.name)
async def form_name(message: Message, state: FSMContext):
    name = message.text.strip()
    if len(name) < 2:
        await message.answer("❌ Iltimos, ismingizni to‘g‘ri kiriting.")
        return

    await state.update_data(name=name)
    await state.set_state(Form.direction)
    await message.answer("🛠 Yo‘nalishingizni tanlang:", reply_markup=directions_kb())


# =========================
#   ANKETA: Yo‘nalish
# =========================
@router.callback_query(Form.direction, F.data.startswith("dir:"))
async def form_direction(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    direction = cb.data.split("dir:", 1)[1]
    await state.update_data(direction=direction)
    await state.set_state(Form.experience)
    await cb.message.answer("🧠 Qancha yil tajribangiz bor, tanlang:", reply_markup=exp_kb())


# =========================
#   ANKETA: Tajriba
# =========================
@router.callback_query(Form.experience, F.data.startswith("exp:"))
async def form_experience(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    exp = cb.data.split("exp:", 1)[1]
    await state.update_data(experience=exp)

    # Xizmatlar (ixtiyoriy)
    await state.set_state(Form.services)
    await cb.message.answer("🧰 Xizmatlaringizni yozing (siz qila oladigan ishlar):", reply_markup=skip_kb("services:skip"))


@router.callback_query(Form.services, F.data == "services:skip")
async def services_skip(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.update_data(services="—")
    await state.set_state(Form.region)
    await cb.message.answer("📍 Hududingizni tanlang:", reply_markup=regions_kb())


@router.message(Form.services)
async def services_text(message: Message, state: FSMContext):
    services = message.text.strip()
    if not services:
        services = "—"
    await state.update_data(services=services)
    await state.set_state(Form.region)
    await message.answer("📍 Hududingizni tanlang:", reply_markup=regions_kb())


# =========================
#   ANKETA: Hudud
# =========================
@router.callback_query(Form.region, F.data.startswith("reg:"))
async def form_region(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    region = cb.data.split("reg:", 1)[1]
    await state.update_data(region=region)

    # Telefon: contact request (reply keyboard) kerak
    await state.set_state(Form.phone)
    await cb.message.answer("📞 Telefon raqamingizni yuboring:", reply_markup=phone_request_kb())


# =========================
#   ANKETA: Telefon
# =========================
@router.message(Form.phone, F.contact)
async def phone_contact(message: Message, state: FSMContext):
    phone = message.contact.phone_number or ""
    phone = normalize_phone(phone)
    await state.update_data(phone=phone)

    # Reply keyboardni olib tashlaymiz
    await message.answer("✅ Qabul qilindi.", reply_markup=ReplyKeyboardRemove())

    # ixtiyoriy ish rasmlari/video bosqichi
    await state.set_state(Form.work_media)
    await state.update_data(work_media_list=[])
    await message.answer(
        "🖼 Ish rasmlari yoki video yuborishingiz mumkin (ixtiyoriy).\n"
        "Bir nechta yuborsangiz ham bo‘ladi.\n\n"
        "Yuborib bo‘lgach <b>✅ Tayyor</b> ni bosing.",
        reply_markup=media_done_kb(),
        parse_mode="HTML"
    )


@router.message(Form.phone)
async def phone_text(message: Message, state: FSMContext):
    text = normalize_phone(message.text or "")
    if len(re.sub(r"[^\d]", "", text)) < 7:
        await message.answer("❌ Telefon raqam noto‘g‘ri ko‘rinmoqda. Pastdagi tugma orqali yuboring.")
        return

    await state.update_data(phone=text)
    await message.answer("✅ Qabul qilindi.", reply_markup=ReplyKeyboardRemove())

    await state.set_state(Form.work_media)
    await state.update_data(work_media_list=[])
    await message.answer(
        "🖼 Ish rasmlari yoki video yuborishingiz mumkin (ixtiyoriy).\n"
        "Bir nechta yuborsangiz ham bo‘ladi.\n\n"
        "Yuborib bo‘lgach <b>✅ Tayyor</b> ni bosing.",
        reply_markup=media_done_kb(),
        parse_mode="HTML"
    )


# =========================
#   ANKETA: Ish rasmlari/video (ixtiyoriy)
# =========================
@router.message(Form.work_media, F.photo)
async def work_media_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    media_list = data.get("work_media_list", [])

    photo = message.photo[-1]
    media_list.append({
        "type": "photo",
        "file_id": photo.file_id,
        "caption": message.caption or ""
    })
    await state.update_data(work_media_list=media_list)

    await message.answer("✅ Qabul qilindi. Yana yuborishingiz mumkin yoki <b>✅ Tayyor</b> ni bosing.", parse_mode="HTML")


@router.message(Form.work_media, F.video)
async def work_media_video(message: Message, state: FSMContext):
    data = await state.get_data()
    media_list = data.get("work_media_list", [])

    media_list.append({
        "type": "video",
        "file_id": message.video.file_id,
        "caption": message.caption or ""
    })
    await state.update_data(work_media_list=media_list)

    await message.answer("✅ Qabul qilindi. Yana yuborishingiz mumkin yoki <b>✅ Tayyor</b> ni bosing.", parse_mode="HTML")


@router.callback_query(Form.work_media, F.data == "media:skip")
async def work_media_skip(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    # media yo'q
    await state.update_data(work_media_list=[])
    await state.set_state(Form.confirm)

    data = await state.get_data()
    await cb.message.answer(build_preview_text(cb.from_user, data), reply_markup=confirm_kb(), parse_mode="HTML")


@router.callback_query(Form.work_media, F.data == "media:done")
async def work_media_done(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(Form.confirm)

    data = await state.get_data()
    await cb.message.answer(build_preview_text(cb.from_user, data), reply_markup=confirm_kb(), parse_mode="HTML")


def build_preview_text(user, data: dict) -> str:
    # Preview - userga ko'rsatish
    telegram = data.get("telegram") or build_profile_html(user)
    name = escape(data.get("name", "—"))
    direction = escape(data.get("direction", "—"))
    exp = escape(str(data.get("experience", "—")))
    
    services = escape(data.get("services", "—"))
    
    region = escape(data.get("region", "—"))
    phone = escape(data.get("phone", "—"))

    return (
        "📋 <b>Anketa ma’lumotlari</b>\n\n"
        f"🧑‍🔧 <b>Ism:</b> {name}\n"
        f"🛠 <b>Yo‘nalish:</b> {direction}\n"
        f"🧠 <b>Tajriba:</b> {exp}\n"
        
        f"🧰 <b>Xizmatlar:</b> {services}\n"
        
        f"📍 <b>Hudud:</b> {region}\n"
        f"📞 <b>Telefon:</b> {phone}\n"
        f"💬 <b>Telegram:</b> {telegram}\n\n"
        "✅ Hammasi to‘g‘rimi?"
    )


# =========================
#   ANKETA: Tasdiqlash
# =========================
@router.callback_query(Form.confirm, F.data == "confirm:yes")
async def confirm_yes(cb: CallbackQuery, state: FSMContext):
    await cb.answer()

    # Adminga yuboramiz
    await send_admin_summary(state, cb)

    await state.clear()
    await cb.message.answer(
        "✅ Anketangiz qabul qilindi.\n"
        "Admin tomonidan tekshirilgach kanalga joylanadi. Rahmat!",
        reply_markup=main_menu_kb()
    )


@router.callback_query(Form.confirm, F.data == "confirm:restart")
async def confirm_restart(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.clear()
    await state.set_state(Form.name)

    # profil linkni yana avtomatik tayyorlaymiz
    await state.update_data(telegram=build_profile_html(cb.from_user))

    await cb.message.answer("🔄 Qaytadan boshladik.\n🧑‍🔧 Ismingizni kiriting:")


@router.callback_query(Form.confirm, F.data == "confirm:menu")
async def confirm_menu(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.clear()
    await cb.message.answer("🏠 Menyu:", reply_markup=main_menu_kb())


# =========================
#   Reklama post yuborish (admin ga yetkazish)
# =========================
@router.message(AdPost.waiting_post)
async def ad_post_receive(message: Message, state: FSMContext):
    # Foydalanuvchi yuborgan postni admin ga yetkazamiz
    u = message.from_user
    full_name = escape(u.full_name or "")
    user_id = u.id
    profile = build_profile_html(u)

    header = (
        "📢 <b>Yangi reklama post keldi</b> ✅\n\n"
        f"👤 <b>Kimdan:</b> {full_name} | ID: <code>{user_id}</code>\n"
        f"🔗 <b>Profil:</b> {profile}\n"
    )

    # Avval info yuboramiz
    await bot.send_message(ADMIN_ID, header, parse_mode="HTML")

    # Keyin postni copy/forward qilamiz (caption ham keladi)
    try:
        await bot.copy_message(
            chat_id=ADMIN_ID,
            from_chat_id=message.chat.id,
            message_id=message.message_id
        )
    except Exception:
        # fallback: hech bo'lmasa matn
        await bot.send_message(ADMIN_ID, f"Post nusxalashda xatolik. Matn:\n{message.text or '—'}")

    await state.clear()
    await message.answer(
        "✅ Qabul qilindi.\nSiz yuborgan reklama admin tomonidan ko‘rib chiqiladi va kanalga joylanadi.Rahmat!.",
        reply_markup=main_menu_kb()
    )


# =========================
#   Run
# =========================
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
