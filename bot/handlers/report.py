from datetime import datetime
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext

from bot.config import Config
from bot.database.queries import get_user, upsert_daily_record, get_daily_record
from bot.keyboards.inline import get_date_picker_keyboard, get_report_confirm_keyboard
from bot.states.states import ReportStates

report_router = Router()


def parse_meal_count(text: str) -> int | None:
    text = text.strip()
    if not text.isdigit():
        return None
    val = int(text)
    if 0 <= val <= 5000:
        return val
    return None


def format_report_summary_card(
    hospital_name: str,
    date_str: str,
    breakfast: int,
    lunch: int,
    dinner: int,
    note: str = ""
) -> str:
    total = breakfast + lunch + dinner
    note_line = f"📝 <b>Eskertiw:</b> {note}\n" if note else ""
    return (
        f"🏥 <b>Emlewxana:</b> {hospital_name}\n"
        f"📅 <b>Sáne:</b> {date_str}\n\n"
        f"☕ <b>Azanǵı awqat:</b> {breakfast} adam\n"
        f"🍲 <b>Túslik (obet):</b> {lunch} adam\n"
        f"🌙 <b>Keshki awqat:</b> {dinner} adam\n"
        "-------------------------------\n"
        f"🔢 <b>Kúnlik jámi portciya:</b> <b>{total}</b> adam\n"
        f"{note_line}\n"
        "Maǵlıwmatlar durıs kiritildime?"
    )


@report_router.message(F.text == "📊 Kúnlik sanlardı kiritip barıw")
async def on_start_daily_report(message: Message, state: FSMContext, config: Config):
    user = await get_user(config.db_path, message.from_user.id)
    if not user or user["status"] != "approved":
        await message.answer("Siz ele tastıyıqlanbaǵansız yamasa dizimnen ótpegeniz.")
        return

    await state.clear()
    await state.set_state(ReportStates.select_date)
    await message.answer(
        "📅 <b>Qaysı kún ushın adam sanların kiritip atırsız?</b>\n"
        "Tómendegi sáneti tańlań:",
        parse_mode="HTML",
        reply_markup=get_date_picker_keyboard()
    )


@report_router.message(F.text == "📋 Búgingi kiritilgen maǵlıwmat")
async def on_view_today_submission(message: Message, config: Config):
    user = await get_user(config.db_path, message.from_user.id)
    if not user or user["status"] != "approved":
        await message.answer("Siz ele tastıyıqlanbaǵansız.")
        return

    today = datetime.now().strftime("%Y-%m-%d")
    record = await get_daily_record(config.db_path, user["hospital_id"], today)
    if not record:
        await message.answer(
            f"ℹ️ Búgingi kún ({today}) ushın ele maǵlıwmat kiritilmegen.\n\n"
            "Kiritiw ushın <b>«📊 Kúnlik sanlardı kiritip barıw»</b> túymesin basıń.",
            parse_mode="HTML"
        )
    else:
        text = format_report_summary_card(
            hospital_name=user["hospital_name"],
            date_str=today,
            breakfast=record["breakfast_count"],
            lunch=record["lunch_count"],
            dinner=record["dinner_count"],
            note=record.get("note", "")
        )
        await message.answer(
            f"✅ <b>Búgingi kúnlik kiritilgen maǵlıwmatıńız:</b>\n\n{text}",
            parse_mode="HTML"
        )


@report_router.callback_query(ReportStates.select_date, F.data.startswith("set_date:"))
async def on_date_picked(callback: CallbackQuery, state: FSMContext):
    date_str = callback.data.split(":")[1]
    await state.update_data(report_date=date_str)
    await state.set_state(ReportStates.waiting_for_breakfast)
    await callback.message.delete()
    await callback.message.answer(
        f"📅 Saylanǵan sáne: <b>{date_str}</b>\n\n"
        "☕ <b>Azanǵı awqatqa</b> neshe adam (pasient)?\n"
        "(Klaviaturadan pútin san kiritiń, mısalı: <code>120</code>):",
        parse_mode="HTML"
    )
    await callback.answer()


@report_router.message(ReportStates.waiting_for_breakfast, F.text)
async def on_breakfast_entered(message: Message, state: FSMContext):
    val = parse_meal_count(message.text)
    if val is None:
        await message.answer("❌ Iltimas, durıs san kiritiń (mısalı: 120):")
        return
    await state.update_data(breakfast=val)
    await state.set_state(ReportStates.waiting_for_lunch)
    await message.answer(
        "🍲 <b>Túslik (obet) ushın</b> neshe adam?\n"
        "(Klaviaturadan pútin san kiritiń, mısalı: <code>120</code>):",
        parse_mode="HTML"
    )


@report_router.message(ReportStates.waiting_for_lunch, F.text)
async def on_lunch_entered(message: Message, state: FSMContext):
    val = parse_meal_count(message.text)
    if val is None:
        await message.answer("❌ Iltimas, durıs san kiritiń (mısalı: 120):")
        return
    await state.update_data(lunch=val)
    await state.set_state(ReportStates.waiting_for_dinner)
    await message.answer(
        "🌙 <b>Keshki awqat ushın</b> neshe adam?\n"
        "(Klaviaturadan pútin san kiritiń, mısalı: <code>115</code>):",
        parse_mode="HTML"
    )


@report_router.message(ReportStates.waiting_for_dinner, F.text)
async def on_dinner_entered(message: Message, state: FSMContext, config: Config):
    val = parse_meal_count(message.text)
    if val is None:
        await message.answer("❌ Iltimas, durıs san kiritiń (mısalı: 115):")
        return
    await state.update_data(dinner=val)

    data = await state.get_data()
    user = await get_user(config.db_path, message.from_user.id)

    summary_card = format_report_summary_card(
        hospital_name=user["hospital_name"],
        date_str=data["report_date"],
        breakfast=data["breakfast"],
        lunch=data["lunch"],
        dinner=val,
        note=""
    )
    await state.set_state(ReportStates.confirm_report)
    await message.answer(
        summary_card,
        parse_mode="HTML",
        reply_markup=get_report_confirm_keyboard()
    )


@report_router.callback_query(F.data == "restart_daily_report")
async def on_restart_daily_report(callback: CallbackQuery, state: FSMContext):
    await state.set_state(ReportStates.select_date)
    await callback.message.edit_text(
        "📅 Sáneti qaytadan tańlań:",
        reply_markup=get_date_picker_keyboard()
    )
    await callback.answer()


@report_router.callback_query(F.data == "confirm_daily_report")
async def on_confirm_daily_report(callback: CallbackQuery, state: FSMContext, config: Config):
    data = await state.get_data()
    user = await get_user(config.db_path, callback.from_user.id)

    await upsert_daily_record(
        db_path=config.db_path,
        hospital_id=user["hospital_id"],
        user_id=callback.from_user.id,
        report_date=data["report_date"],
        breakfast=data["breakfast"],
        lunch=data["lunch"],
        dinner=data["dinner"],
        note=data.get("note", "")
    )

    await state.clear()
    await callback.message.edit_text(
        "✅ <b>Maǵlıwmatlar qabıllandı hám bazaǵa jazıldı!</b>\n\n"
        "«Lakoma» katering xızmeti ushı sanlar tiykarında awqat penen támiyinleydi.",
        parse_mode="HTML"
    )
    await callback.answer()


@report_router.callback_query(F.data == "cancel_action")
async def on_cancel_action(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.delete()
    await callback.answer("Biykar etildi")
