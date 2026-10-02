from aiogram import Router, F
from aiogram.filters import CommandStart
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext

from bot.config import Config
from bot.database.queries import get_user, get_regions, get_all_hospitals
from bot.keyboards.reply import get_main_hospital_keyboard, get_admin_keyboard
from bot.keyboards.inline import get_regions_inline_keyboard, get_hospitals_inline_keyboard
from bot.states.states import RegistrationStates

start_router = Router()


@start_router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, config: Config):
    await state.clear()
    telegram_id = message.from_user.id

    # Check if user is configured as Admin in config
    if telegram_id in config.admin_ids:
        await message.answer(
            "Assalawma áleykum, húrmetli Administrator!\n"
            "«Lakoma» Katering Servisi basqarıw paneline xosh keldińiz.",
            reply_markup=get_admin_keyboard(),
        )
        return

    # Check existing user in database
    user = await get_user(config.db_path, telegram_id)
    if user:
        if user["status"] == "approved":
            await message.answer(
                f"Assalawma áleykum, {user['full_name']}!\n"
                f"🏥 Emlewxana: <b>{user['hospital_name']}</b> ({user['region_name']})\n\n"
                "Kúnlik adam sanların kiritip barıw ushın tómendegi menyudan paydalanıń:",
                parse_mode="HTML",
                reply_markup=get_main_hospital_keyboard(),
            )
            return
        elif user["status"] == "pending":
            await message.answer(
                "⏳ <b>Dizimnen ótiw sorawıńız kútilip atır.</b>\n\n"
                "Lakoma administratorı tastıyıqlaǵannan soń sizge xabarnama baradı.",
                parse_mode="HTML",
            )
            return
        elif user["status"] == "rejected":
            await message.answer(
                "❌ <b>Keshirersiz, sizge ruqsat berilmedi.</b>\n"
                "Tolıq maǵlıwmat ushın Lakoma administraciyasına baylanısıń.",
                parse_mode="HTML",
            )
            return

    # New user: Start Registration directly by selecting hospital
    hospitals = await get_all_hospitals(config.db_path)
    await state.set_state(RegistrationStates.waiting_for_hospital)
    await message.answer(
        "Assalawma áleykum!\n"
        "«Lakoma» Katering xızmeti kúnlik awqat támiynatı botına xosh keldińiz.\n\n"
        "Sistemaǵa qosılıw ushın <b>Emlewxanańızdı (mákemeńizdi)</b> tańlań:",
        parse_mode="HTML",
        reply_markup=get_hospitals_inline_keyboard(hospitals, show_back=False),
    )


@start_router.message(F.text.in_(["📞 Menedjer menen baylanıs", "Menedjer menen baylanıs", "📞 Lakoma dispetcher menen baylanıs"]))
async def on_contact_manager(message: Message):
    call_kb = InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📞 Qońıraw qılıw (+998953720110)", url="tel:+998953720110")]
        ]
    )
    await message.answer(
        "📞 <b>«Lakoma» Katering menedjeri menen baylanıs:</b>\n\n"
        "☎️ <b>Telefon:</b> <a href=\"tel:+998953720110\">+998 95 372 01 10</a>\n\n"
        "💬 Qálegen soraw, usınıs yamasa kúnlik menyu boyınsha qońıraw qılıwıńız múmkin.",
        parse_mode="HTML",
        reply_markup=call_kb,
    )
