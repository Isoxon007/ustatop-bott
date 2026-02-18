import os
import asyncio
from typing import Optional, Dict, Any

from aiogram import Bot, Dispatcher, F
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)
from aiogram.filters import CommandStart
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage


# ========== CONFIG ==========
BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN topilmadi. Koyeb Environment'ga BOT_TOKEN qo'shing.")
if not ADMIN_ID_RAW.isdigit():
    raise RuntimeError("ADMIN_ID noto‘g‘ri. Koyeb Environment'ga faqat raqam ko‘rinishida ADMIN_ID kiriting.")

ADMIN_ID = int(ADMIN_ID_RAW)


# ========== BOT INIT ==========
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=MemoryStorage())


# ========== DATA ==========
# Yo‘nalishlar (o'rtacha darajada, juda mayda emas)
DIRECTIONS = [
    "Santexnik",
    "Elektrik",
    "Gaz ustasi",
    "Konditsioner ustasi",
    "Mebel ustasi",
    "Qurilish ustasi(beton,suvoq ishlari",
    "Kafel ustasi",
    "Bo‘yoqchi(ichki va tashqi bezak)",
    "Svarchik",
    "Tom ustasi",
    "Gipsakarton usta",
    "Maishiy-texnika usta",
    "Gipsokarton",
    "Pol ustasi ",
    "Plastik/Alyumin rom ustasi ",
    "Eshik-zamok ustasi",
    "Oddiy ishchi(mardikor)",
    "Boshqa",
]

# Namangan bo‘yicha “tumani” bilan
DISTRICTS = [
    "Namangan shahar",
    "Chortoq tumani",
    "Chust tumani",
    "Kosonsoy tumani",
    "Mingbuloq tumani",
    "Norin tumani",
    "Pop tumani",
    "To‘raqo‘rg‘on tumani",
    "Uchqo‘rg‘on tumani",
    "Uychi tumani",
    "Yangiqo‘rg‘on tumani",
]


# ========== INLINE KEYBOARDS ==========
def kb_home() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📝 Anketa to‘ldirish", callback_data="home:anketa")],
        [InlineKeyboardButton(text="📢 Reklama post yuborish", callback_data="home:ad")],
    ])

def kb_back_home() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="home:back")]
    ])

def kb_skip_next() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➡️ Keyingisi", callback_data="anketa:skip_what_can")],
        [InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="home:back")],
    ])

def kb_confirm() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tasdiqlash", callback_data="anketa:confirm")],
        [InlineKeyboardButton(text="🔄 Qayta to‘ldirish", callback_data="anketa:restart")],
        [InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="home:back")],
    ])

def kb_directions(page: int = 0, per_page: int = 8) -> InlineKeyboardMarkup:
    start = page * per_page
    items = DIRECTIONS[start:start + per_page]
    rows = [[InlineKeyboardButton(text=it, callback_data=f"anketa:dir:{it}")] for it in items]

    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"anketa:dirpage:{page-1}"))
    if start + per_page < len(DIRECTIONS):
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"anketa:dirpage:{page+1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="home:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_experience() -> InlineKeyboardMarkup:
    # 0..10+
    rows = []
    for i in range(0, 11):
        rows.append([InlineKeyboardButton(text=f"{i} yil" if i < 10 else "10+ yil", callback_data=f"anketa:exp:{i}")])
    rows.append([InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="home:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_districts(page: int = 0, per_page: int = 8) -> InlineKeyboardMarkup:
    start = page * per_page
    items = DISTRICTS[start:start + per_page]
    rows = [[InlineKeyboardButton(text=it, callback_data=f"anketa:dist:{it}")] for it in items]

    nav = []
    if start > 0:
        nav.append(InlineKeyboardButton(text="⬅️", callback_data=f"anketa:distpage:{page-1}"))
    if start + per_page < len(DISTRICTS):
        nav.append(InlineKeyboardButton(text="➡️", callback_data=f"anketa:distpage:{page+1}"))
    if nav:
        rows.append(nav)

    rows.append([InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="home:back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def kb_phone_tip() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📞 Raqamni kontakt ko‘rinishida yuboring", callback_data="anketa:phone_help")],
        [InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="home:back")],
    ])

def kb_photos_done() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Tayyor", callback_data="anketa:photos_done")],
        [InlineKeyboardButton(text="⏭ O‘tkazib yuborish", callback_data="anketa:photos_skip")],
        [InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="home:back")],
    ])

def kb_ad_done() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Yana post yuborish", callback_data="ad:again")],
        [InlineKeyboardButton(text="🏠 Bosh sahifa", callback_data="home:back")],
    ])


# ========== FSM STATES ==========
class Anketa(StatesGroup):
    name = State()
    direction = State()
    exp = State()
    what_can = State()         # ixtiyoriy
    district = State()
    phone = State()
    telegram = State()
    photos = State()           # ixtiyoriy (photo/video)
    confirm = State()

class AdPost(StatesGroup):
    waiting_post = State()


# ========== HELPERS ==========
def user_identity(m: Message) -> str:
    u = m.from_user
    uname = f"@{u.username}" if u.username else "username yo‘q"
    full = (u.full_name or "").strip()
    return f"{full} | {uname} | id={u.id}"

async def go_home_chat(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("🏠 Bosh sahifa:", reply_markup=kb_home())

async def go_home_cb(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.message.edit_text("🏠 Bosh sahifa:", reply_markup=kb_home())
    await call.answer()

def anketa_preview(data: Dict[str, Any]) -> str:
    # chiroyli ko‘rinish
    exp_val = data.get("exp")
    exp_txt = "—" if exp_val is None else (f"{exp_val} yil" if exp_val < 10 else "10+ yil")
    what_can = data.get("what_can") or "—"
    tg = data.get("telegram") or "—"
    phone = data.get("phone") or "—"
    return (
        "🧾 *Anketa ma’lumotlari*\n\n"
        f"🧑‍🔧 *Ism:* {data.get('name','—')}\n"
        f"🛠 *Yo‘nalish:* {data.get('direction','—')}\n"
        f"🧠 *Tajriba:* {exp_txt}\n"
        f"🧰 *Nimalar qila olasiz (ixtiyoriy):* {what_can}\n"
        f"📍 *Hudud:* {data.get('district','—')}\n"
        f"📞 *Telefon:* {phone}\n"
        f"💬 *Telegram:* {tg}\n\n"
        "Ma’lumotlar to‘g‘rimi?"
    )


# ========== START / HOME ==========
@dp.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Assalomu alaykum!\n\n"
        "UstaTop Namangan botiga xush kelibsiz.\n"
        "Bot orqali anketa to‘ldirishingiz yoki reklama postingizni yuborishingiz mumkin.\n\n"
        "Kerakli bo‘limni tanlang:",
        reply_markup=kb_home()
    )

@dp.callback_query(F.data == "home:back")
async def cb_home_back(call: CallbackQuery, state: FSMContext):
    await go_home_cb(call, state)

@dp.callback_query(F.data == "home:anketa")
async def cb_start_anketa(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(Anketa.name)
    await call.message.edit_text("👤 Ismingizni kiriting:", reply_markup=kb_back_home())
    await call.answer()

@dp.callback_query(F.data == "home:ad")
async def cb_start_ad(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(AdPost.waiting_post)
    await call.message.edit_text(
        "📢 *Reklama post yuborish*\n\n"
        "Rasm/video yuboring va tagiga izoh (caption) yozing.\n"
        "Yoki oddiy matn post ham yuborsangiz bo‘ladi.",
        reply_markup=kb_back_home(),
        parse_mode="Markdown"
    )
    await call.answer()


# ========== ANKETA FLOW ==========
@dp.message(Anketa.name)
async def anketa_name(message: Message, state: FSMContext):
    txt = (message.text or "").strip()
    if len(txt) < 2:
        await message.answer("Iltimos, ismingizni to‘g‘ri yozing (kamida 2 ta harf).", reply_markup=kb_back_home())
        return
    await state.update_data(name=txt)
    await state.set_state(Anketa.direction)
    await message.answer("🛠 Yo‘nalishingizni tanlang:", reply_markup=kb_directions(0))

@dp.callback_query(F.data.startswith("anketa:dirpage:"))
async def cb_dir_page(call: CallbackQuery, state: FSMContext):
    page = int(call.data.split(":")[-1])
    await call.message.edit_reply_markup(reply_markup=kb_directions(page))
    await call.answer()

@dp.callback_query(F.data.startswith("anketa:dir:"))
async def cb_dir_pick(call: CallbackQuery, state: FSMContext):
    direction = call.data.split("anketa:dir:", 1)[1]
    await state.update_data(direction=direction)
    await state.set_state(Anketa.exp)
    await call.message.edit_text("🧠 Tajribangizni tanlang:", reply_markup=kb_experience())
    await call.answer()

@dp.callback_query(F.data.startswith("anketa:exp:"))
async def cb_exp_pick(call: CallbackQuery, state: FSMContext):
    exp = int(call.data.split(":")[-1])
    await state.update_data(exp=exp)
    await state.set_state(Anketa.what_can)
    await call.message.edit_text(
        "🧰 Bu sohada nimalar qila olasiz? *(ixtiyoriy)*\n\n"
        "Xohlasangiz yozing yoki pastdagi ➡️ *Keyingisi* ni bosing.",
        reply_markup=kb_skip_next(),
        parse_mode="Markdown"
    )
    await call.answer()

@dp.callback_query(F.data == "anketa:skip_what_can")
async def cb_skip_what_can(call: CallbackQuery, state: FSMContext):
    await state.update_data(what_can=None)
    await state.set_state(Anketa.district)
    await call.message.edit_text("📍 Hududingizni tanlang:", reply_markup=kb_districts(0))
    await call.answer()

@dp.message(Anketa.what_can)
async def anketa_what_can(message: Message, state: FSMContext):
    txt = (message.text or "").strip()
    # juda uzun bo'lib ketmasin
    if len(txt) > 300:
        await message.answer("Juda uzun bo‘lib ketdi. 300 belgidan oshirmang 🙂", reply_markup=kb_skip_next())
        return
    await state.update_data(what_can=txt)
    await state.set_state(Anketa.district)
    await message.answer("📍 Hududingizni tanlang:", reply_markup=kb_districts(0))

@dp.callback_query(F.data.startswith("anketa:distpage:"))
async def cb_dist_page(call: CallbackQuery, state: FSMContext):
    page = int(call.data.split(":")[-1])
    await call.message.edit_reply_markup(reply_markup=kb_districts(page))
    await call.answer()

@dp.callback_query(F.data.startswith("anketa:dist:"))
async def cb_dist_pick(call: CallbackQuery, state: FSMContext):
    district = call.data.split("anketa:dist:", 1)[1]
    await state.update_data(district=district)
    await state.set_state(Anketa.phone)
    await call.message.edit_text(
        "📞 Telefon raqamingizni yuboring.\n\n"
        "Masalan: +998901234567\n"
        "Yoki kontakt (contact) ko‘rinishida yuborsangiz ham bo‘ladi.",
        reply_markup=kb_phone_tip()
    )
    await call.answer()

@dp.callback_query(F.data == "anketa:phone_help")
async def cb_phone_help(call: CallbackQuery):
    await call.answer(
        "Telefonni kontakt ko‘rinishida yuborish uchun Telegramda 📎 (attach) → Contact tanlang.",
        show_alert=True
    )

@dp.message(Anketa.phone)
async def anketa_phone(message: Message, state: FSMContext):
    phone: Optional[str] = None

    if message.contact and message.contact.phone_number:
        phone = message.contact.phone_number.strip()
        if not phone.startswith("+"):
            phone = "+" + phone

    if not phone:
        txt = (message.text or "").strip().replace(" ", "")
        # juda sodda tekshiruv
        if txt.startswith("+998") and len(txt) >= 13:
            phone = txt

    if not phone:
        await message.answer("Telefon raqam noto‘g‘ri. Masalan: +998901234567", reply_markup=kb_phone_tip())
        return

    await state.update_data(phone=phone)
    await state.set_state(Anketa.telegram)
    await message.answer("💬 Telegram username’ingizni yuboring (masalan: @username):", reply_markup=kb_back_home())

@dp.message(Anketa.telegram)
async def anketa_telegram(message: Message, state: FSMContext):
    txt = (message.text or "").strip()
    if not txt.startswith("@") or len(txt) < 3:
        await message.answer("Username noto‘g‘ri. Masalan: @username", reply_markup=kb_back_home())
        return

    await state.update_data(telegram=txt)
    await state.set_state(Anketa.photos)

    await message.answer(
        "🖼 Ish rasmlari *(ixtiyoriy)*\n\n"
        "1–5 ta rasm/video yuborishingiz mumkin.\n"
        "Bo‘lmasa pastdagi *O‘tkazib yuborish* ni bosing.",
        reply_markup=kb_photos_done(),
        parse_mode="Markdown"
    )

@dp.message(Anketa.photos, F.photo | F.video)
async def anketa_photos_collect(message: Message, state: FSMContext):
    data = await state.get_data()
    media = data.get("media", [])
    if len(media) >= 5:
        await message.answer("Maksimum 5 ta fayl. Endi ✅ Tayyor ni bosing.", reply_markup=kb_photos_done())
        return

    if message.photo:
        file_id = message.photo[-1].file_id
        media.append({"type": "photo", "file_id": file_id})
    elif message.video:
        file_id = message.video.file_id
        media.append({"type": "video", "file_id": file_id})

    await state.update_data(media=media)
    await message.answer(f"✅ Qabul qilindi. Hozircha {len(media)}/5 ta.\nYana yuboring yoki ✅ Tayyor ni bosing.", reply_markup=kb_photos_done())

@dp.callback_query(F.data == "anketa:photos_skip")
async def cb_photos_skip(call: CallbackQuery, state: FSMContext):
    await state.update_data(media=[])
    await state.set_state(Anketa.confirm)
    data = await state.get_data()
    await call.message.edit_text(anketa_preview(data), reply_markup=kb_confirm(), parse_mode="Markdown")
    await call.answer()

@dp.callback_query(F.data == "anketa:photos_done")
async def cb_photos_done(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    media = data.get("media", [])
    # agar user "tayyor" bossa va hech narsa yubormagan bo'lsa ham bo'ladi
    await state.update_data(media=media if media else [])
    await state.set_state(Anketa.confirm)
    data = await state.get_data()
    await call.message.edit_text(anketa_preview(data), reply_markup=kb_confirm(), parse_mode="Markdown")
    await call.answer()

@dp.callback_query(F.data == "anketa:restart")
async def cb_anketa_restart(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await state.set_state(Anketa.name)
    await call.message.edit_text("👤 Ismingizni kiriting:", reply_markup=kb_back_home())
    await call.answer()

@dp.callback_query(F.data == "anketa:confirm")
async def cb_anketa_confirm(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    await call.answer()

    # Adminga yuboriladigan xabar (kim yuborgani ham chiqadi)
    sender = call.from_user
    sender_line = f"{sender.full_name} | @{sender.username}" if sender.username else f"{sender.full_name} | username yo‘q"
    header = (
        "🆕 *Yangi anketa keldi!* ✅\n\n"
        f"👤 *Kimdan:* {sender_line}\n"
        f"🆔 *ID:* `{sender.id}`\n\n"
    )
    text_to_admin = header + anketa_preview(data)

    # Avval matn yuboramiz
    await bot.send_message(ADMIN_ID, text_to_admin, parse_mode="Markdown")

    # Keyin media bo'lsa, alohida yuboramiz (caption bilan emas, tartibli)
    media = data.get("media", [])
    for item in media:
        if item["type"] == "photo":
            await bot.send_photo(ADMIN_ID, item["file_id"])
        else:
            await bot.send_video(ADMIN_ID, item["file_id"])

    await state.clear()
    await call.message.edit_text(
        "✅ Anketangiz qabul qilindi.\nTez orada admin ko‘rib chiqadi va kanalga joylanadi. Rahmat!",
        reply_markup=kb_home()
    )


# ========== AD POST FLOW ==========
@dp.message(AdPost.waiting_post)
async def ad_post_receive(message: Message, state: FSMContext):
    # User reklama post yuboradi: matn yoki rasm/video + caption
    sender_info = user_identity(message)

    sent_any = False

    if message.photo:
        file_id = message.photo[-1].file_id
        caption = (message.caption or "").strip()
        cap = f"📢 *Reklama post*\n👤 {sender_info}\n\n{caption}" if caption else f"📢 *Reklama post*\n👤 {sender_info}"
        await bot.send_photo(ADMIN_ID, file_id, caption=cap[:1024], parse_mode="Markdown")
        sent_any = True

    elif message.video:
        file_id = message.video.file_id
        caption = (message.caption or "").strip()
        cap = f"📢 *Reklama post*\n👤 {sender_info}\n\n{caption}" if caption else f"📢 *Reklama post*\n👤 {sender_info}"
        await bot.send_video(ADMIN_ID, file_id, caption=cap[:1024], parse_mode="Markdown")
        sent_any = True

    else:
        txt = (message.text or "").strip()
        if txt:
            await bot.send_message(ADMIN_ID, f"📢 *Reklama post (matn)*\n👤 {sender_info}\n\n{txt}", parse_mode="Markdown")
            sent_any = True

    if not sent_any:
        await message.answer("Iltimos rasm/video yoki matn yuboring. (Bo‘sh post qabul qilinmaydi)", reply_markup=kb_back_home())
        return

    await message.answer(
        "✅ Qabul qilindi!\nAdmin ko‘rib chiqadi, talablarimizga to‘g‘ri kelsa kanalga joylanadi. Rahmat!",
        reply_markup=kb_ad_done()
    )
    await state.clear()

@dp.callback_query(F.data == "ad:again")
async def cb_ad_again(call: CallbackQuery, state: FSMContext):
    await state.set_state(AdPost.waiting_post)
    await call.message.edit_text(
        "📢 Yana reklama post yuboring (rasm/video + caption yoki matn).",
        reply_markup=kb_back_home()
    )
    await call.answer()


# ========== FALLBACKS ==========
@dp.message()
async def fallback(message: Message):
    # foydalanuvchi holatsiz yozib yuborsa
    await message.answer("Iltimos /start ni bosing va menyudan tanlang.", reply_markup=kb_home())

@dp.callback_query()
async def fallback_cb(call: CallbackQuery):
    await call.answer("Iltimos menyudan foydalaning.", show_alert=False)


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
