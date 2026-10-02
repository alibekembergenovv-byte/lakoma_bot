import re
from aiogram import Router, F, Bot
from aiogram.types import CallbackQuery, Message
from aiogram.fsm.context import FSMContext

from bot.config import Config
from bot.database.queries import (
    get_regions,
    get_hospitals_by_region,
    get_hospital_by_id,
    upsert_user,
)
from bot.keyboards.inline import (
    get_regions_inline_keyboard,
    get_hospitals_inline_keyboard,
    get_moderation_keyboard,
)
from bot.keyboards.reply import get_contact_request_keyboard
from bot.states.states import RegistrationStates

registration_router = Router()


def validate_phone_number(raw_phone: str) -> str | None:
    digits = re.sub(r"\D", "", raw_phone)
    if digits.startswith("998") and len(digits) == 12:
        return f"+{digits}"
    elif len(digits) == 9:
        return f"+998{digits}"
    return None


def format_registration_alert(
    user_name: str, phone: str, hospital_name: str, region_name: str
) -> str:
    return (
        "🆕 <b>Jańa bolnica dizimnen ótti!</b>\n\n"
        f"📍 <b>Rayon:</b> {region_name}\n"
        f"🏥 <b>Emlewxana:</b> {hospital_name}\n"
        f"👤 <b>Juwapker xızmetker:</b> {user_name}\n"
        f"📞 <b>Telefon:</b> {phone}\n\n"
        "Xızmetkerdi tastıyıqlaysız ba?"
    )


@registration_router.callback_query(
    RegistrationStates.waiting_for_region, F.data.startswith("reg_region:")
)
async def on_region_selected(callback: CallbackQuery, state: FSMContext, config: Config):
    if not callback.data:
        return
    region_id = int(callback.data.split(":")[1])
    await state.update_data(region_id=region_id)

    hospitals = await get_hospitals_by_region(config.db_path, region_id)
    await state.set_state(RegistrationStates.waiting_for_hospital)
    if callback.message:
        await callback.message.edit_text(
            "🏥 Endi ózińiz jumıs isleytuǵın <b>Emlewxananı</b> tańlań:",
            parse_mode="HTML",
            reply_markup=get_hospitals_inline_keyboard(hospitals),
        )
    await callback.answer()


@registration_router.callback_query(F.data == "back_to_regions")
async def on_back_to_regions(callback: CallbackQuery, state: FSMContext, config: Config):
    regions = await get_regions(config.db_path)
    await state.set_state(RegistrationStates.waiting_for_region)
    if callback.message:
        await callback.message.edit_text(
            "Rayonıńızdı tańlań:",
            reply_markup=get_regions_inline_keyboard(regions),
        )
    await callback.answer()


@registration_router.callback_query(
    RegistrationStates.waiting_for_hospital, F.data.startswith("reg_hosp:")
)
async def on_hospital_selected(callback: CallbackQuery, state: FSMContext, config: Config):
    if not callback.data:
        return
    hospital_id = int(callback.data.split(":")[1])
    hosp_info = await get_hospital_by_id(config.db_path, hospital_id)
    if not hosp_info:
        await callback.answer("Emlewxana tabılmadı", show_alert=True)
        return

    await state.update_data(
        hospital_id=hospital_id,
        hospital_name=hosp_info["hospital_name"],
        region_name=hosp_info["region_name"],
    )

    await state.set_state(RegistrationStates.waiting_for_name)
    if callback.message:
        await callback.message.delete()
        await callback.message.answer(
            f"🏥 Saylandı: <b>{hosp_info['hospital_name']}</b>\n\n"
            "Iltimas, óz <b>Atıńız hám Familiyańızdı</b> kiritiń:\n"
            "(Mısalı: <i>Azamat Berdiyarov</i>)",
            parse_mode="HTML",
        )
    await callback.answer()


@registration_router.message(RegistrationStates.waiting_for_name, F.text)
async def on_name_entered(message: Message, state: FSMContext):
    full_name = message.text.strip() if message.text else ""
    if len(full_name) < 3:
        await message.answer("Iltimas, atıńız hám familiyańızdı tolıq kiritiń:")
        return
    await state.update_data(full_name=full_name)
    await state.set_state(RegistrationStates.waiting_for_phone)
    await message.answer(
        "Raxmet! Endi baylanıs ushın <b>telefon nomerińizdi</b> jiberiń.\n"
        "Tómendegi <b>«📱 Telefon nomerimdi jiberiw»</b> túymesin basıń yamasa qoldan jazıń (+998901234567):",
        parse_mode="HTML",
        reply_markup=get_contact_request_keyboard(),
    )


@registration_router.message(RegistrationStates.waiting_for_phone, F.contact | F.text)
async def on_phone_submitted(message: Message, state: FSMContext, bot: Bot, config: Config):
    if message.contact:
        phone = message.contact.phone_number
        if not phone.startswith("+"):
            phone = f"+{phone}"
    else:
        text = message.text.strip() if message.text else ""
        phone = validate_phone_number(text)
        if not phone:
            await message.answer("❌ Nomer durıs kiritilmedi. Mısalı: +998901234567 túrinde jazıń:")
            return

    data = await state.get_data()
    telegram_id = message.from_user.id
    full_name = data["full_name"]
    hospital_id = data["hospital_id"]

    await upsert_user(
        db_path=config.db_path,
        telegram_id=telegram_id,
        full_name=full_name,
        phone=phone,
        hospital_id=hospital_id,
        role="hospital_user",
        status="pending",
    )

    await state.clear()
    await message.answer(
        "✅ <b>Dizimnen ótiw sorawıńız qabıllandı!</b>\n\n"
        "Lakoma administratorı tastıyıqlaǵannan soń sizge xabar beremiz hám kúnlik sanlardı kiritiw menyusı ashıladı.",
        parse_mode="HTML",
    )

    # Notify admins
    alert_text = format_registration_alert(
        user_name=full_name,
        phone=phone,
        hospital_name=data["hospital_name"],
        region_name=data["region_name"],
    )
    for admin_id in config.admin_ids:
        try:
            await bot.send_message(
                chat_id=admin_id,
                text=alert_text,
                parse_mode="HTML",
                reply_markup=get_moderation_keyboard(telegram_id),
            )
        except Exception:
            pass
