from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def get_main_hospital_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📊 Kúnlik sanlardı kiritip barıw")],
            [KeyboardButton(text="📋 Búgingi kiritilgen maǵlıwmat")],
            [KeyboardButton(text="📞 Menedjer menen baylanıs")],
        ],
        resize_keyboard=True,
    )


def get_contact_request_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📱 Telefon nomerimdi jiberiw", request_contact=True)]
        ],
        resize_keyboard=True,
        one_time_keyboard=True,
    )


def get_admin_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="📈 Búgingi ulıwma jıyıntıq"),
                KeyboardButton(text="📅 Aylıq esabat"),
            ],
            [
                KeyboardButton(text="📥 Excel esabat júklew"),
                KeyboardButton(text="⚠️ Kiritpegenler dizimi"),
            ],
            [
                KeyboardButton(text="👥 Tastıyıqlaw kútilip atırǵanlar"),
                KeyboardButton(text="📢 Kiritpegenlerge esletpe jiberiw"),
            ],
        ],
        resize_keyboard=True,
    )
