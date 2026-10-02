from datetime import datetime, timedelta
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def get_regions_inline_keyboard(regions: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for r in regions:
        buttons.append(
            [InlineKeyboardButton(text=r["name"], callback_data=f"reg_region:{r['id']}")]
        )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_hospitals_inline_keyboard(hospitals: list[dict]) -> InlineKeyboardMarkup:
    buttons = []
    for h in hospitals:
        buttons.append(
            [InlineKeyboardButton(text=h["name"], callback_data=f"reg_hosp:{h['id']}")]
        )
    buttons.append(
        [InlineKeyboardButton(text="⬅️ Rayondı qayta tańlaw", callback_data="back_to_regions")]
    )
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def get_moderation_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Tastıyıqlaw", callback_data=f"mod_approve:{user_id}"),
                InlineKeyboardButton(text="❌ Biykarlaw", callback_data=f"mod_reject:{user_id}"),
            ]
        ]
    )


def get_date_picker_keyboard() -> InlineKeyboardMarkup:
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text=f"📅 Búgin ({today})", callback_data=f"set_date:{today}"),
                InlineKeyboardButton(text=f"📅 Erteń ({tomorrow})", callback_data=f"set_date:{tomorrow}"),
            ],
            [
                InlineKeyboardButton(text="❌ Biykar etiw", callback_data="cancel_action"),
            ],
        ]
    )


def get_report_confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Maǵlıwmattı tastıyıqlaw", callback_data="confirm_daily_report"),
                InlineKeyboardButton(text="✏️ Qayta kiritisi", callback_data="restart_daily_report"),
            ],
            [
                InlineKeyboardButton(text="❌ Biykar etiw", callback_data="cancel_action"),
            ],
        ]
    )


def get_excel_options_keyboard() -> InlineKeyboardMarkup:
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=f"📊 Búgingi esabat ({today})", callback_data=f"excel_day:{today}")],
            [InlineKeyboardButton(text=f"📊 Keshegi esabat ({yesterday})", callback_data=f"excel_day:{yesterday}")],
            [InlineKeyboardButton(text="📅 Usı aydıń tolıq esabatı", callback_data="excel_current_month")],
            [InlineKeyboardButton(text="❌ Jabıw", callback_data="cancel_action")],
        ]
    )
