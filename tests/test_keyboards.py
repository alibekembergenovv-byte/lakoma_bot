from datetime import datetime, timedelta
from aiogram.types import ReplyKeyboardMarkup, InlineKeyboardMarkup
from bot.states.states import RegistrationStates, ReportStates, AdminStates
from bot.keyboards.reply import (
    get_main_hospital_keyboard,
    get_contact_request_keyboard,
    get_admin_keyboard,
)
from bot.keyboards.inline import (
    get_regions_inline_keyboard,
    get_hospitals_inline_keyboard,
    get_moderation_keyboard,
    get_date_picker_keyboard,
    get_report_confirm_keyboard,
    get_excel_options_keyboard,
)


def test_states_defined():
    # Registration states
    assert RegistrationStates.waiting_for_region is not None
    assert RegistrationStates.waiting_for_hospital is not None
    assert RegistrationStates.waiting_for_name is not None
    assert RegistrationStates.waiting_for_phone is not None

    # Report states
    assert ReportStates.select_date is not None
    assert ReportStates.waiting_for_breakfast is not None
    assert ReportStates.waiting_for_lunch is not None
    assert ReportStates.waiting_for_dinner is not None
    assert ReportStates.waiting_for_note is not None
    assert ReportStates.confirm_report is not None

    # Admin states
    assert AdminStates.waiting_for_custom_date is not None
    assert AdminStates.waiting_for_custom_month is not None
    assert AdminStates.waiting_for_broadcast_text is not None


def test_reply_keyboards():
    # Hospital main keyboard
    main_kb = get_main_hospital_keyboard()
    assert isinstance(main_kb, ReplyKeyboardMarkup)
    assert main_kb.resize_keyboard is True
    button_texts = [btn.text for row in main_kb.keyboard for btn in row]
    assert "📊 Kúnlik sanlardı kiritip barıw" in button_texts
    assert "📋 Búgingi kiritilgen maǵlıwmat" in button_texts
    assert "📞 Menedjer menen baylanıs" in button_texts

    # Contact request keyboard
    contact_kb = get_contact_request_keyboard()
    assert isinstance(contact_kb, ReplyKeyboardMarkup)
    assert contact_kb.resize_keyboard is True
    assert contact_kb.one_time_keyboard is True
    contact_btn = contact_kb.keyboard[0][0]
    assert contact_btn.text == "📱 Telefon nomerimdi jiberiw"
    assert contact_btn.request_contact is True

    # Admin keyboard
    admin_kb = get_admin_keyboard()
    assert isinstance(admin_kb, ReplyKeyboardMarkup)
    assert admin_kb.resize_keyboard is True
    admin_buttons = [btn.text for row in admin_kb.keyboard for btn in row]
    assert "📈 Búgingi ulıwma jıyıntıq" in admin_buttons
    assert "📥 Excel esabat júklew" in admin_buttons
    assert "⚠️ Kiritpegenler dizimi" in admin_buttons
    assert "👥 Tastıyıqlaw kútilip atırǵanlar" in admin_buttons
    assert "📢 Kiritpegenlerge esletpe jiberiw" in admin_buttons


def test_inline_keyboards():
    # Regions keyboard
    regions = [
        {"id": 1, "name": "Nókis qalası"},
        {"id": 2, "name": "Qaraózek rayonı"},
    ]
    regions_kb = get_regions_inline_keyboard(regions)
    assert isinstance(regions_kb, InlineKeyboardMarkup)
    assert len(regions_kb.inline_keyboard) == 2
    assert regions_kb.inline_keyboard[0][0].text == "Nókis qalası"
    assert regions_kb.inline_keyboard[0][0].callback_data == "reg_region:1"
    assert regions_kb.inline_keyboard[1][0].text == "Qaraózek rayonı"
    assert regions_kb.inline_keyboard[1][0].callback_data == "reg_region:2"

    # Hospitals keyboard
    hospitals = [
        {"id": 10, "name": "Respublika balalar ftiziatriyası"},
        {"id": 11, "name": "Respublika qan quyıw orayı"},
    ]
    hospitals_kb = get_hospitals_inline_keyboard(hospitals)
    assert isinstance(hospitals_kb, InlineKeyboardMarkup)
    assert len(hospitals_kb.inline_keyboard) == 3  # 2 hospitals + 1 back button
    assert hospitals_kb.inline_keyboard[0][0].text == "Respublika balalar ftiziatriyası"
    assert hospitals_kb.inline_keyboard[0][0].callback_data == "reg_hosp:10"
    assert hospitals_kb.inline_keyboard[1][0].text == "Respublika qan quyıw orayı"
    assert hospitals_kb.inline_keyboard[1][0].callback_data == "reg_hosp:11"
    assert hospitals_kb.inline_keyboard[2][0].callback_data == "back_to_regions"

    # Moderation keyboard
    mod_kb = get_moderation_keyboard(998877)
    assert isinstance(mod_kb, InlineKeyboardMarkup)
    assert len(mod_kb.inline_keyboard[0]) == 2
    assert mod_kb.inline_keyboard[0][0].callback_data == "mod_approve:998877"
    assert mod_kb.inline_keyboard[0][1].callback_data == "mod_reject:998877"

    # Date picker keyboard
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")
    date_kb = get_date_picker_keyboard()
    assert isinstance(date_kb, InlineKeyboardMarkup)
    date_callbacks = [btn.callback_data for row in date_kb.inline_keyboard for btn in row]
    assert f"set_date:{today}" in date_callbacks
    assert f"set_date:{tomorrow}" in date_callbacks
    assert "cancel_action" in date_callbacks

    # Report confirm keyboard
    confirm_kb = get_report_confirm_keyboard()
    assert isinstance(confirm_kb, InlineKeyboardMarkup)
    confirm_callbacks = [btn.callback_data for row in confirm_kb.inline_keyboard for btn in row]
    assert "confirm_daily_report" in confirm_callbacks
    assert "restart_daily_report" in confirm_callbacks
    assert "cancel_action" in confirm_callbacks

    # Excel options keyboard
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")
    excel_kb = get_excel_options_keyboard()
    assert isinstance(excel_kb, InlineKeyboardMarkup)
    excel_callbacks = [btn.callback_data for row in excel_kb.inline_keyboard for btn in row]
    assert f"excel_day:{today}" in excel_callbacks
    assert f"excel_day:{yesterday}" in excel_callbacks
    assert "excel_current_month" in excel_callbacks
    assert "cancel_action" in excel_callbacks
