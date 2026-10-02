from datetime import datetime
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile

from bot.config import Config
from bot.database.queries import (
    get_daily_summary,
    get_missing_hospitals,
    get_pending_users,
    set_user_status,
    get_records_for_period,
    get_user,
)
from bot.keyboards.inline import get_moderation_keyboard, get_excel_options_keyboard
from bot.keyboards.reply import get_main_hospital_keyboard
from bot.services.excel_service import generate_daily_excel, generate_monthly_excel

admin_router = Router()


def is_admin(telegram_id: int, config: Config) -> bool:
    return telegram_id in config.admin_ids


def format_admin_summary_text(summary: dict) -> str:
    lines = [
        f"📊 <b>KÚNLIK AWQAT ESABATÍ — {summary['date']}</b>\n",
        f"🏥 <b>Kiritken bolnicalar:</b> {summary['submitted_hospitals']} / {summary['total_hospitals']}",
        "------------------------------------",
        f"☕ <b>Jámi azanǵı awqat:</b> <b>{summary['total_breakfast']:,}</b> adam",
        f"🍲 <b>Jámi túslik (obet):</b> <b>{summary['total_lunch']:,}</b> adam",
        f"🌙 <b>Jámi keshki awqat:</b> <b>{summary['total_dinner']:,}</b> adam",
        "------------------------------------",
        f"🔢 <b>KÚNLIK JÁMI PORTCIYA:</b> <b>{summary['total_all']:,}</b> dana\n",
        "<b>Bolnicalar boyınsha:</b>",
    ]
    if not summary.get("items"):
        lines.append("<i>Ele hesh qaysı bolnica maǵlıwmat kiritpedi.</i>")
    else:
        for idx, item in enumerate(summary["items"], 1):
            lines.append(
                f"{idx}. <b>{item['hospital_name']}</b> ({item['region_name']}): "
                f"{item['breakfast_count']} / {item['lunch_count']} / {item['dinner_count']} "
                f"(Jámi: {item['total_daily']})"
            )
    return "\n".join(lines)


def format_monthly_summary_text(records: list[dict], month_str: str, start_date: str, end_date: str) -> str:
    if not records:
        return (
            f"📅 <b>«LAKOMA» KATERING — AYLIQ ESABAT ({month_str})</b>\n"
            f"📆 <i>Aralıq: {start_date} — {end_date}</i>\n\n"
            "ℹ️ <i>Bul ay ushın házirshe hesh qanday kúnlik esabat kiritilmegen.</i>"
        )

    # Group records by hospital
    hospital_stats = {}
    for r in records:
        h_name = r.get("hospital_name", "Belgisiz")
        if h_name not in hospital_stats:
            hospital_stats[h_name] = {
                "breakfast": 0,
                "lunch": 0,
                "dinner": 0,
                "total": 0,
                "days": 0,
            }
        hospital_stats[h_name]["breakfast"] += r.get("breakfast_count", 0)
        hospital_stats[h_name]["lunch"] += r.get("lunch_count", 0)
        hospital_stats[h_name]["dinner"] += r.get("dinner_count", 0)
        hospital_stats[h_name]["total"] += r.get("total_daily", 0)
        hospital_stats[h_name]["days"] += 1

    total_b = sum(s["breakfast"] for s in hospital_stats.values())
    total_l = sum(s["lunch"] for s in hospital_stats.values())
    total_d = sum(s["dinner"] for s in hospital_stats.values())
    total_all = sum(s["total"] for s in hospital_stats.values())

    lines = [
        f"📅 <b>«LAKOMA» KATERING — AYLIQ ESABAT ({month_str})</b>",
        f"📆 <i>Aralıq: {start_date} — {end_date}</i>",
        "------------------------------------",
        "🏥 <b>Mákemeler (Bolnicalar) boyınsha jámi:</b>\n",
    ]

    for idx, (h_name, stats) in enumerate(hospital_stats.items(), 1):
        lines.append(
            f"{idx}. <b>{h_name}</b> ({stats['days']} kún kiritilgen):\n"
            f"   ☕ Azan: <b>{stats['breakfast']:,}</b> | 🍲 Obet: <b>{stats['lunch']:,}</b> | 🌙 Kesh: <b>{stats['dinner']:,}</b>\n"
            f"   👉 Aylıq jámi: <b>{stats['total']:,}</b> portciya\n"
        )

    lines.extend([
        "------------------------------------",
        "📊 <b>AYLIQ ULÍWMA JÁMI:</b>",
        f"☕ Jámi azanǵı awqat: <b>{total_b:,}</b> adam",
        f"🍲 Jámi túslik (obet): <b>{total_l:,}</b> adam",
        f"🌙 Jámi keshki awqat: <b>{total_d:,}</b> adam",
        "------------------------------------",
        f"🔢 <b>AYLIQ JÁMI AWQAT SANÍ:</b> <b>{total_all:,}</b> portciya",
    ])
    return "\n".join(lines)


@admin_router.message(F.text == "📈 Búgingi ulıwma jıyıntıq")
async def on_admin_today_summary(message: Message, config: Config):
    if not is_admin(message.from_user.id, config):
        return
    today = datetime.now().strftime("%Y-%m-%d")
    summary = await get_daily_summary(config.db_path, today)
    text = format_admin_summary_text(summary)
    await message.answer(text, parse_mode="HTML")


@admin_router.message(F.text.in_(["📅 Aylıq esabat", "Aylıq esabat"]))
async def on_admin_month_summary(message: Message, config: Config):
    if not is_admin(message.from_user.id, config):
        return
    now = datetime.now()
    start_date = now.strftime("%Y-%m-01")
    end_date = now.strftime("%Y-%m-%d")
    month_str = now.strftime("%Y-%m")

    records = await get_records_for_period(config.db_path, start_date, end_date)
    text_report = format_monthly_summary_text(records, month_str, start_date, end_date)
    await message.answer(text_report, parse_mode="HTML")

    file_path = config.exports_dir / f"lakoma_monthly_{month_str}.xlsx"
    generate_monthly_excel(records, month_str, file_path)

    doc = FSInputFile(file_path, filename=f"Lakoma_Aylıq_Esabat_{month_str}.xlsx")
    await message.answer_document(
        document=doc,
        caption=f"📊 <b>«Lakoma» katering — {month_str} aydıń tolıq Excel esabatı</b>",
        parse_mode="HTML",
    )


@admin_router.message(F.text == "⚠️ Kiritpegenler dizimi")
async def on_admin_missing_list(message: Message, config: Config):
    if not is_admin(message.from_user.id, config):
        return
    today = datetime.now().strftime("%Y-%m-%d")
    missing = await get_missing_hospitals(config.db_path, today)

    if not missing:
        await message.answer(
            f"🎉 Barlıq bolnicalar búgingi ({today}) sanlardı kiritip boldı!"
        )
        return

    lines = [
        f"⚠️ <b>Búgingi ({today}) san kiritpegen bolnicalar ({len(missing)} dana):</b>\n"
    ]
    for idx, item in enumerate(missing, 1):
        contact = (
            f"({item['user_name']} - {item['user_phone']})"
            if item.get("user_name")
            else "<i>(Xızmetker dizimnen ótpegen)</i>"
        )
        lines.append(
            f"{idx}. <b>{item['hospital_name']}</b> ({item['region_name']}) — {contact}"
        )

    lines.append(
        "\nBarlıq kiritpegenlerge esletpe jiberiw ushın «📢 Kiritpegenlerge esletpe jiberiw» túymesin basıń."
    )
    await message.answer("\n".join(lines), parse_mode="HTML")


@admin_router.message(F.text == "📢 Kiritpegenlerge esletpe jiberiw")
async def on_broadcast_reminders(message: Message, bot: Bot, config: Config):
    if not is_admin(message.from_user.id, config):
        return
    today = datetime.now().strftime("%Y-%m-%d")
    missing = await get_missing_hospitals(config.db_path, today)

    sent_count = 0
    for item in missing:
        user_tg_id = item.get("user_telegram_id")
        if user_tg_id:
            try:
                await bot.send_message(
                    chat_id=user_tg_id,
                    text=(
                        f"⚠️ <b>Húrmetli {item.get('user_name', 'xızmetker')}!</b>\n\n"
                        f"«Lakoma» katering xızmeti ushın <b>{item['hospital_name']}</b> boyınsha "
                        f"búgingi ({today}) kúnlik adam sanların kiritiwińiz kerek.\n\n"
                        "Iltimas, <b>«📊 Kúnlik sanlardı kiritip barıw»</b> túymesin basıp sanlardı kiritiń!"
                    ),
                    parse_mode="HTML",
                )
                sent_count += 1
            except Exception:
                pass

    await message.answer(
        f"📢 Jámi <b>{sent_count}</b> bolnica xızmetkerine esletpe jiberildi!",
        parse_mode="HTML",
    )


@admin_router.message(F.text == "👥 Tastıyıqlaw kútilip atırǵanlar")
async def on_admin_pending_users(message: Message, config: Config):
    if not is_admin(message.from_user.id, config):
        return
    pending = await get_pending_users(config.db_path)
    if not pending:
        await message.answer("Tastıyıqlaw kútilip atırǵan jańa bolnica joq.")
        return

    for u in pending:
        await message.answer(
            f"🆕 <b>Kútilip atırǵan dizim:</b>\n"
            f"👤 Atı: {u['full_name']}\n"
            f"📞 Telefon: {u['phone']}\n"
            f"🏥 Bolnica: {u['hospital_name']} ({u['region_name']})\n",
            parse_mode="HTML",
            reply_markup=get_moderation_keyboard(u["telegram_id"]),
        )


@admin_router.callback_query(F.data.startswith("mod_approve:"))
async def on_approve_user(callback: CallbackQuery, bot: Bot, config: Config):
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Ruxsat joq!", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    await set_user_status(config.db_path, user_id, "approved")

    await callback.message.edit_text(
        f"{callback.message.text}\n\n✅ <b>Tastıyıqlandı!</b>",
        parse_mode="HTML",
    )
    await callback.answer("Tastıyıqlandı!")

    try:
        await bot.send_message(
            chat_id=user_id,
            text=(
                "🎉 <b>Xosh xabar!</b>\n\n"
                "Lakoma administraciyası sizdiń akkauntıńızdı tastıyıqladı.\n"
                "Endi kúnlik adam sanların kiritip barsańız boladı!"
            ),
            parse_mode="HTML",
            reply_markup=get_main_hospital_keyboard(),
        )
    except Exception:
        pass


@admin_router.callback_query(F.data.startswith("mod_reject:"))
async def on_reject_user(callback: CallbackQuery, bot: Bot, config: Config):
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Ruxsat joq!", show_alert=True)
        return
    user_id = int(callback.data.split(":")[1])
    await set_user_status(config.db_path, user_id, "rejected")

    await callback.message.edit_text(
        f"{callback.message.text}\n\n❌ <b>Biykar etildi!</b>",
        parse_mode="HTML",
    )
    await callback.answer("Biykar etildi!")

    try:
        await bot.send_message(
            chat_id=user_id,
            text="❌ Sizdiń sorawıńız Lakoma administraciyası tárepinen biykar etildi.",
        )
    except Exception:
        pass


@admin_router.message(F.text == "📥 Excel esabat júklew")
async def on_admin_excel_menu(message: Message, config: Config):
    if not is_admin(message.from_user.id, config):
        return
    await message.answer(
        "📥 <b>Qaysı waqıt aralıǵı ushın Excel esabat kerek?</b>",
        parse_mode="HTML",
        reply_markup=get_excel_options_keyboard(),
    )


@admin_router.callback_query(F.data.startswith("excel_day:"))
async def on_excel_day_download(callback: CallbackQuery, config: Config):
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Ruxsat joq!", show_alert=True)
        return
    day_str = callback.data.split(":")[1]
    summary = await get_daily_summary(config.db_path, day_str)

    file_path = config.exports_dir / f"lakoma_daily_{day_str}.xlsx"
    generate_daily_excel(summary, file_path)

    doc = FSInputFile(file_path, filename=f"Lakoma_Esabat_{day_str}.xlsx")
    await callback.message.answer_document(
        document=doc,
        caption=f"📊 <b>«Lakoma» katering — {day_str} kúngi awqat esabatı</b>",
        parse_mode="HTML",
    )
    await callback.answer()


@admin_router.callback_query(F.data == "excel_current_month")
async def on_excel_month_download(callback: CallbackQuery, config: Config):
    if not is_admin(callback.from_user.id, config):
        await callback.answer("Ruxsat joq!", show_alert=True)
        return
    now = datetime.now()
    start_date = now.strftime("%Y-%m-01")
    end_date = now.strftime("%Y-%m-%d")
    month_str = now.strftime("%Y-%m")

    records = await get_records_for_period(config.db_path, start_date, end_date)
    text_report = format_monthly_summary_text(records, month_str, start_date, end_date)
    await callback.message.answer(text_report, parse_mode="HTML")

    file_path = config.exports_dir / f"lakoma_monthly_{month_str}.xlsx"
    generate_monthly_excel(records, month_str, file_path)

    doc = FSInputFile(file_path, filename=f"Lakoma_Aylıq_Esabat_{month_str}.xlsx")
    await callback.message.answer_document(
        document=doc,
        caption=f"📊 <b>«Lakoma» katering — {month_str} aydıń tolıq esabatı</b>",
        parse_mode="HTML",
    )
    await callback.answer()
