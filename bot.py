import os
import re
import asyncio
from typing import List, Dict, Any, Optional, Tuple

from aiogram import Bot, Dispatcher, Router, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    ReplyKeyboardMarkup,
    KeyboardButton,
    ReplyKeyboardRemove,
    InputMediaPhoto,
    InputMediaVideo,
)
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# =========================
# ENV
# =========================
TOKEN = os.getenv("TOKEN", "").strip()
ADMIN_CHAT_ID = os.getenv("ADMIN_CHAT_ID", "").strip()  # masalan: 1586199040

if not TOKEN:
    raise RuntimeError("TOKEN env topilmadi. Koyeb/Railway/PC da TOKEN ni env qilib qo'ying.")
if not ADMIN_CHAT_ID or not ADMIN_CHAT_ID.lstrip("-").isdigit():
    raise RuntimeError("ADMIN_CHAT_ID env noto'g'ri. Masalan: 1586199040 yoki -100xxxx")

ADMIN_CHAT_ID = int(ADMIN_CHAT_ID)

# =========================
# DATA (yo'nalish + hudud)
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
    "Oddiy ishchi(mardikor)",
    "Boshqa",
]

# Namangan hududlari (tumani qo'shilgan)
REGIONS = [
    "Namangan shahri",
    "Mingbuloq tumani",
    "Kosonsoy tumani",
    "Namangan tumani",
    "Norin tumani",
    "Pop tumani",
    "To'raqo'rg'on tumani",
    "Uchqo'rg'on tumani",
    "Uychi tumani",
    "Chortoq tumani",
    "Chust tumani",
    "Yangiqo'rg'on tumani",
]

EXPERIENCE_OPTIONS = [ "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "10+"]

# =========================
# FSM
# =========================
class Form(StatesGroup):
    name = State()
    direction = State()
    direction_other = State()
    experience = State()
    services = State()          # ixtiyoriy
    region = State()
    phone = State()
    telegram = State()          # ixtiyoriy (username bo'lmasa profil link)
    work_media = State()        # ixtiyoriy
    confirm = State()

# =========================
# HELPERS
# =========================
def esc(s: str) -> str:
    # HTML escape minimal
    return (
        s.replace("&", "&amp;")
         .replace("<", "&lt;")
         .replace(">", "&gt;")
    )

def profile_link_html(user) -> str:
    """
    Adminga ham, userga ham ishlaydigan profil havola:
    username bo'lsa t.me link, bo'lmasa tg://user?id=...
    """
    if getattr(user, "username", None):
        u = user.username
        return f'<a href="https://t.me/{esc(u)}">@{esc(u)}</a>'
    return f'<a href="tg://user?id={user.id}">Profil</a>'

def main_menu_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Anketa to‘ldirish", callback_data="menu:anketa")],
        [InlineKeyboardButton(text="📣 Reklama post yuborish", callback_data="menu:reklama")],
    ])

def back_home_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="menu:home")]
    ])

def skip_kb(cb_data: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Keyingisi", callback_data=cb_data)]
    ])

def directions_kb() -> InlineKeyboardMarkup:
    rows = []
    for d in DIRECTIONS:
        rows.append([InlineKeyboardButton(text=d, callback_data=f"dir:{d}")])
    rows.append([InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def regions_kb() -> InlineKeyboardMarkup:
    rows = []
    for r in REGIONS:
        rows.append([InlineKeyboardButton(text=r, callback_data=f"reg:{r}")])
    rows.append([InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def exp_kb() -> InlineKeyboardMarkup:
    rows = []
    # 2 tadan qilib chiroyli chiqishi uchun
    pair = []
    for x in EXPERIENCE_OPTIONS:
        pair.append(InlineKeyboardButton(text=f"{x} yil" if x.isdigit() else f"{x} yil", callback_data=f"exp:{x}"))
        if len(pair) == 2:
            rows.append(pair)
            pair = []
    if pair:
        rows.append(pair)
    rows.append([InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="menu:home")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def media_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tayyor", callback_data="media:done")],
        [InlineKeyboardButton(text="⏭ O‘tkazib yuborish", callback_data="media:skip")],
        [InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="menu:home")]
    ])

def confirm_kb() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="cfm:yes")],
        [InlineKeyboardButton(text="🔄 Qayta to‘ldirish", callback_data="cfm:restart")],
        [InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="menu:home")],
    ])

def phone_request_kb() -> ReplyKeyboardMarkup:
    # Telegramda contact request faqat ReplyKeyboard bilan bo'ladi (inline bilan bo'lmaydi)
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📞 Telefon raqamni yuborish", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
        input_field_placeholder="Telefon tugmasini bosing"
    )

def normalize_username(text: str) -> Optional[str]:
    t = (text or "").strip()
    if not t:
        return None
    if t.startswith("@"):
        t = t[1:]
    # username: 5-32, harf/raqam/_ (Telegram qoidasi)
    if re.fullmatch(r"[A-Za-z0-9_]{5,32}", t):
        return "@" + t
    return None

def build_preview(data: Dict[str, Any], user) -> str:
    name = esc(data.get("name", "—"))
    direction = esc(data.get("direction", "—"))
    exp = esc(data.get("experience", "—"))
    services = esc(data.get("services", "—"))
    region = esc(data.get("region", "—"))
    phone = esc(data.get("phone", "—"))
    telegram = data.get("telegram") or profile_link_html(user)  # html bo'lishi mumkin

    return (
        "🧾 <b>Anketa ma’lumotlari</b>\n\n"
        f"🧑‍🔧 <b>Ism:</b> {name}\n"
        f"🛠 <b>Yo‘nalish:</b> {direction}\n"
        f"🧠 <b>Tajriba:</b> {exp}\n"
        f"🧰 <b>Xizmatlar:</b> {services}\n"
        f"📍 <b>Hudud:</b> {region}\n"
        f"📞 <b>Telefon:</b> {phone}\n"
        f"💬 <b>Telegram:</b> {telegram}\n"
    )

async def send_admin_anketa(bot: Bot, data: Dict[str, Any], user) -> None:
    """
    Admin xabari: faqat profil link + anketa.
    Media bo'lsa: avval media group yuboriladi, keyin tekst.
    """
    # media
    media_list: List[Dict[str, str]] = data.get("work_media_list", []) or []
    if media_list:
        media_group = []
        for item in media_list[:10]:  # telegram media group limit ~10
            if item["type"] == "photo":
                media_group.append(InputMediaPhoto(media=item["file_id"]))
            elif item["type"] == "video":
                media_group.append(InputMediaVideo(media=item["file_id"]))
        if media_group:
            await bot.send_media_group(chat_id=ADMIN_CHAT_ID, media=media_group)

    telegram_val = data.get("telegram") or profile_link_html(user)
    # telegram_val ba'zan '@username' bo'ladi, ba'zan html link bo'ladi — ikkalasi ham ok

    txt = (
        "🆕 <b>Yangi anketa</b> ✅\n\n"
        f"🔗 <b>Profil:</b> {profile_link_html(user)}\n\n"
        f"🧑‍🔧 <b>Ism:</b> {esc(data.get('name','—'))}\n"
        f"🛠 <b>Yo‘nalish:</b> {esc(data.get('direction','—'))}\n"
        f"🧠 <b>Tajriba:</b> {esc(data.get('experience','—'))}\n"
        f"🧰 <b>Xizmatlar:</b> {esc(data.get('services','—'))}\n"
        f"📍 <b>Hudud:</b> {esc(data.get('region','—'))}\n"
        f"📞 <b>Telefon:</b> {esc(data.get('phone','—'))}\n"
        f"💬 <b>Telegram:</b> {telegram_val}\n"
    )
    await bot.send_message(chat_id=ADMIN_CHAT_ID, text=txt, parse_mode=ParseMode.HTML, disable_web_page_preview=True)

async def send_admin_reklama(bot: Bot, msg: Message) -> None:
    """
    Reklama post: caption yo'qolmasligi uchun copy_message ishlatamiz.
    Keyin ustiga profil link yozib qo'yamiz.
    """
    await bot.send_message(
        chat_id=ADMIN_CHAT_ID,
        text=f"📣 <b>Yangi reklama post</b>\n🔗 <b>Profil:</b> {profile_link_html(msg.from_user)}",
        parse_mode=ParseMode.HTML,
        disable_web_page_preview=True
    )
    # copy_message caption bilan birga keladi
    await bot.copy_message(
        chat_id=ADMIN_CHAT_ID,
        from_chat_id=msg.chat.id,
        message_id=msg.message_id
    )

# =========================
# ROUTER
# =========================
router = Router()

WELCOME_TEXT = (
    "👋 Assalomu alaykum!\n\n"
    
    "UstaTop Namangan botiga xush kelibsiz.\n"
    "Bot orqali anketa to‘ldirishingiz yoki reklama postingizni yuborishingiz mumkin.\n\n"
    
    "Kerakli bo‘limni tanlang:"
)

# /start
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())

# Home menu
@router.callback_query(F.data == "menu:home")
async def cb_home(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.answer()
    await cb.message.answer(WELCOME_TEXT, reply_markup=main_menu_kb())

# Menu -> anketa
@router.callback_query(F.data == "menu:anketa")
async def cb_anketa(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.clear()
    await state.set_state(Form.name)
    await cb.message.answer(
        "🧑‍🔧 Ismingizni kiriting:",
        reply_markup=back_home_kb()
    )

@router.message(Form.name)
async def st_name(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if len(text) < 2:
        await message.answer("❗️Ism juda qisqa. Qaytadan kiriting:")
        return
    await state.update_data(name=text)
    await state.set_state(Form.direction)
    await message.answer(
        "🛠 Yo‘nalishingizni tanlang:",
        reply_markup=directions_kb()
    )

@router.callback_query(Form.direction, F.data.startswith("dir:"))
async def st_direction(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    direction = cb.data.split(":", 1)[1]
    if direction == "Boshqa":
        await state.set_state(Form.direction_other)
        await cb.message.answer("🛠 Yo‘nalishingizni yozib yuboring:", reply_markup=back_home_kb())
        return

    await state.update_data(direction=direction)
    await state.set_state(Form.experience)
    await cb.message.answer("🧠 Tajribangizni tanlang:", reply_markup=exp_kb())

@router.message(Form.direction_other)
async def st_direction_other(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if len(text) < 2:
        await message.answer("❗️Yo‘nalish juda qisqa. Qaytadan yozing:")
        return
    await state.update_data(direction=text)
    await state.set_state(Form.experience)
    await message.answer("🧠 Tajribangizni tanlang:", reply_markup=exp_kb())

@router.callback_query(Form.experience, F.data.startswith("exp:"))
async def st_exp(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    exp = cb.data.split(":", 1)[1]
    exp_text = f"{exp} yil"
    await state.update_data(experience=exp_text)

    # ixtiyoriy xizmatlar
    await state.set_state(Form.services)
    await cb.message.answer(
        "🧰 Xizmatlaringizni yozing.\nMasalan: kran o‘rnatish, unitaz almashtirish, quvur tortish.\n\n"
        "Agar yozmasangiz ➡️ Keyingisi ni bosing.",
        reply_markup=skip_kb("srv:skip")
    )

@router.callback_query(Form.services, F.data == "srv:skip")
async def st_services_skip(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.update_data(services="—")
    await state.set_state(Form.region)
    await cb.message.answer("📍 Hududingizni tanlang:", reply_markup=regions_kb())

@router.message(Form.services)
async def st_services_text(message: Message, state: FSMContext):
    text = (message.text or "").strip()
    if not text:
        text = "—"
    await state.update_data(services=text)
    await state.set_state(Form.region)
    await message.answer("📍 Hududingizni tanlang:", reply_markup=regions_kb())

@router.callback_query(Form.region, F.data.startswith("reg:"))
async def st_region(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    region = cb.data.split(":", 1)[1]
    await state.update_data(region=region)

    # phone request (reply keyboard — majburiy)
    await state.set_state(Form.phone)
    await cb.message.answer(
        "📞 Telefon raqamingizni yuboring.\nQuyidagi tugmani bosib raqamni avtomatik yuboring:",
        reply_markup=phone_request_kb()
    )

@router.message(Form.phone, F.contact)
async def st_phone_contact(message: Message, state: FSMContext):
    phone = (message.contact.phone_number or "").strip()
    if not phone:
        await message.answer("❗️Telefon topilmadi. Qayta yuboring.")
        return

    await state.update_data(phone=phone)
    # reply keyboardni olib tashlaymiz va yana inline davom etamiz
    await message.answer("✅ Qabul qilindi.", reply_markup=ReplyKeyboardRemove())

    await state.set_state(Form.telegram)
    await message.answer(
        "💬 Telegram username’ingizni yuboring (masalan: @username).\n"
        "Agar username bo‘lmasa ➡️ Keyingisi ni bosing.",
        reply_markup=skip_kb("tg:skip")
    )

@router.message(Form.phone)
async def st_phone_text_fallback(message: Message, state: FSMContext):
    # foydalanuvchi contact yubormasa
    await message.answer(
        "❗️Iltimos, pastdagi 📞 tugmani bosib telefonni avtomatik yuboring.",
        reply_markup=phone_request_kb()
    )

@router.callback_query(Form.telegram, F.data == "tg:skip")
async def st_tg_skip(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.update_data(telegram=profile_link_html(cb.from_user))

    await state.set_state(Form.work_media)
    await state.update_data(work_media_list=[])
    await cb.message.answer(
        "🖼 Ish rasmlari yoki video yuborishingiz mumkin (ixtiyoriy).\n"
        "Bir nechta yuborsangiz ham bo‘ladi.\n\n"
        "Yuborib bo‘lgach <b>✅ Tayyor</b> ni bosing.",
        reply_markup=media_kb(),
        parse_mode=ParseMode.HTML
    )

@router.message(Form.telegram)
async def st_tg_text(message: Message, state: FSMContext):
    usern = normalize_username(message.text or "")
    if usern:
        await state.update_data(telegram=usern)
    else:
        # username noto'g'ri yoki yo'q — profil link
        await state.update_data(telegram=profile_link_html(message.from_user))

    await state.set_state(Form.work_media)
    await state.update_data(work_media_list=[])
    await message.answer(
        "🖼 Ish rasmlari yoki video yuborishingiz mumkin (ixtiyoriy).\n"
        "Bir nechta yuborsangiz ham bo‘ladi.\n\n"
        "Yuborib bo‘lgach <b>✅ Tayyor</b> ni bosing.",
        reply_markup=media_kb(),
        parse_mode=ParseMode.HTML
    )

@router.message(Form.work_media, F.photo)
async def st_media_photo(message: Message, state: FSMContext):
    data = await state.get_data()
    arr = data.get("work_media_list", []) or []
    file_id = message.photo[-1].file_id
    arr.append({"type": "photo", "file_id": file_id})
    await state.update_data(work_media_list=arr)
    await message.answer("✅ Rasm qabul qilindi. Yana yuborishingiz mumkin yoki <b>✅ Tayyor</b> bosing.", parse_mode=ParseMode.HTML, reply_markup=media_kb())

@router.message(Form.work_media, F.video)
async def st_media_video(message: Message, state: FSMContext):
    data = await state.get_data()
    arr = data.get("work_media_list", []) or []
    file_id = message.video.file_id
    arr.append({"type": "video", "file_id": file_id})
    await state.update_data(work_media_list=arr)
    await message.answer("✅ Video qabul qilindi. Yana yuborishingiz mumkin yoki <b>✅ Tayyor</b> bosing.", parse_mode=ParseMode.HTML, reply_markup=media_kb())

@router.callback_query(Form.work_media, F.data == "media:skip")
async def st_media_skip(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.update_data(work_media_list=[])
    await state.set_state(Form.confirm)
    data = await state.get_data()
    await cb.message.answer(build_preview(data, cb.from_user), parse_mode=ParseMode.HTML, reply_markup=confirm_kb(), disable_web_page_preview=True)

@router.callback_query(Form.work_media, F.data == "media:done")
async def st_media_done(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.set_state(Form.confirm)
    data = await state.get_data()
    await cb.message.answer(build_preview(data, cb.from_user), parse_mode=ParseMode.HTML, reply_markup=confirm_kb(), disable_web_page_preview=True)

@router.callback_query(Form.confirm, F.data == "cfm:restart")
async def st_restart(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.clear()
    await state.set_state(Form.name)
    await cb.message.answer("🧑‍🔧 Ismingizni kiriting:", reply_markup=back_home_kb())

@router.callback_query(Form.confirm, F.data == "cfm:yes")
async def st_confirm(cb: CallbackQuery, state: FSMContext, bot: Bot):
    await cb.answer()
    data = await state.get_data()

    # admin ga yuborish
    await send_admin_anketa(bot, data, cb.from_user)

    await state.clear()
    await cb.message.answer(
        "✅ Anketangiz qabul qilindi.\nTez orada kanalga joylanadi. Rahmat!",
        reply_markup=main_menu_kb()
    )

# Menu -> reklama
@router.callback_query(F.data == "menu:reklama")
async def cb_reklama(cb: CallbackQuery, state: FSMContext):
    await cb.answer()
    await state.clear()
    await state.update_data(waiting_reklama=True)
    await cb.message.answer(
        "📣 Reklama postingizni yuboring.\n"
        "Rasm/video bo‘lsa, albatta tagiga matn ham yozing.\n\n"
        
        "Yuborganingizdan so‘ng admin ko‘rib chiqadi.",
        reply_markup=back_home_kb()
    )

# Reklama post qabul (photo/video/caption bilan)
@router.message(F.photo | F.video)
async def reklama_media_any(message: Message, state: FSMContext, bot: Bot):
    data = await state.get_data()
    if not data.get("waiting_reklama"):
        return  # oddiy media (anketa media bosqichidan tashqari) — e'tiborsiz

    # adminga yuborish (caption ham saqlanadi)
    await send_admin_reklama(bot, message)

    await state.clear()
    await message.answer(
        "✅ Qabul qilindi.\nReklama postingiz admin tomonidan ko‘rib chiqiladi.",
        reply_markup=main_menu_kb()
    )

@router.message()
async def fallback(message: Message, state: FSMContext):
    """
    Agar user chalkashib boshqa narsa yozsa.
    """
    # agar reklama kutayotgan bo'lsa, media so'raymiz
    data = await state.get_data()
    if data.get("waiting_reklama"):
        await message.answer("❗️Iltimos, reklama uchun rasm yoki video yuboring.", reply_markup=back_home_kb())
        return

    await message.answer("ℹ️ /start ni bosing va menyudan tanlang.", reply_markup=main_menu_kb())

# =========================
# MAIN
# =========================
async def main():
    bot = Bot(TOKEN, parse_mode=ParseMode.HTML)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
