from aiogram.fsm.state import State, StatesGroup


class RegistrationStates(StatesGroup):
    waiting_for_region = State()
    waiting_for_hospital = State()
    waiting_for_name = State()
    waiting_for_phone = State()


class ReportStates(StatesGroup):
    select_date = State()
    waiting_for_breakfast = State()
    waiting_for_lunch = State()
    waiting_for_dinner = State()
    waiting_for_note = State()
    confirm_report = State()


class AdminStates(StatesGroup):
    waiting_for_custom_date = State()
    waiting_for_custom_month = State()
    waiting_for_broadcast_text = State()
