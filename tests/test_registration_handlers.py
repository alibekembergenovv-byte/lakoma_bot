import pytest
from unittest.mock import AsyncMock
from pathlib import Path

from bot.config import Config
from bot.database.db import init_db
from bot.database.queries import upsert_user, get_user, get_regions, get_hospitals_by_region
from bot.handlers.registration import (
    validate_phone_number,
    format_registration_alert,
    on_region_selected,
    on_back_to_regions,
    on_hospital_selected,
    on_name_entered,
    on_phone_submitted,
)
from bot.handlers.start import cmd_start
from bot.states.states import RegistrationStates


def test_validate_phone_number():
    assert validate_phone_number("+998901234567") == "+998901234567"
    assert validate_phone_number("90 123 45 67") == "+998901234567"
    assert validate_phone_number("998912345678") == "+998912345678"
    assert validate_phone_number("+998 (90) 123-45-67") == "+998901234567"
    assert validate_phone_number("invalid") is None
    assert validate_phone_number("12345") is None
    assert validate_phone_number("") is None


def test_format_registration_alert():
    text = format_registration_alert(
        user_name="Berdiyarov Azamat",
        phone="+998901234567",
        hospital_name="Qaraózek RMO",
        region_name="Qaraózek rayonı",
    )
    assert "Jańa bolnica dizimnen ótti" in text
    assert "Berdiyarov Azamat" in text
    assert "+998901234567" in text
    assert "Qaraózek RMO" in text
    assert "Qaraózek rayonı" in text


@pytest.mark.asyncio
async def test_cmd_start_admin(tmp_path: Path):
    db_file = tmp_path / "test_reg.db"
    await init_db(db_file)
    config = Config(
        bot_token="test_token",
        admin_ids=[111222],
        db_path=db_file,
        exports_dir=tmp_path / "exports",
    )
    message = AsyncMock()
    message.from_user.id = 111222
    state = AsyncMock()

    await cmd_start(message, state, config)
    state.clear.assert_awaited_once()
    assert message.answer.call_count == 1
    args, kwargs = message.answer.call_args
    assert "Administrator" in args[0]


@pytest.mark.asyncio
async def test_cmd_start_user_branches(tmp_path: Path):
    db_file = tmp_path / "test_reg.db"
    await init_db(db_file)
    config = Config(
        bot_token="test_token",
        admin_ids=[111222],
        db_path=db_file,
        exports_dir=tmp_path / "exports",
    )

    # 1. Approved user
    await upsert_user(
        db_path=config.db_path,
        telegram_id=2001,
        full_name="Approved Doctor",
        phone="+998901111111",
        hospital_id=1,
        role="hospital_user",
        status="approved",
    )

    msg_appr = AsyncMock()
    msg_appr.from_user.id = 2001
    state = AsyncMock()

    await cmd_start(msg_appr, state, config)
    args, kwargs = msg_appr.answer.call_args
    assert "Approved Doctor" in args[0]
    assert kwargs.get("reply_markup") is not None

    # 2. Pending user
    await upsert_user(
        db_path=config.db_path,
        telegram_id=2002,
        full_name="Pending Doctor",
        phone="+998902222222",
        hospital_id=1,
        role="hospital_user",
        status="pending",
    )
    msg_pend = AsyncMock()
    msg_pend.from_user.id = 2002
    await cmd_start(msg_pend, state, config)
    args, _ = msg_pend.answer.call_args
    assert "kútilip atır" in args[0]

    # 3. Rejected user
    await upsert_user(
        db_path=config.db_path,
        telegram_id=2003,
        full_name="Rejected Doctor",
        phone="+998903333333",
        hospital_id=1,
        role="hospital_user",
        status="rejected",
    )
    msg_rej = AsyncMock()
    msg_rej.from_user.id = 2003
    await cmd_start(msg_rej, state, config)
    args, _ = msg_rej.answer.call_args
    assert "ruqsat berilmedi" in args[0]

    # 4. New user
    msg_new = AsyncMock()
    msg_new.from_user.id = 2004
    await cmd_start(msg_new, state, config)
    state.set_state.assert_awaited_with(RegistrationStates.waiting_for_hospital)
    args, kwargs = msg_new.answer.call_args
    assert "Emlewxanańızdı" in args[0]
    assert kwargs.get("reply_markup") is not None


@pytest.mark.asyncio
async def test_registration_flow_handlers(tmp_path: Path):
    db_file = tmp_path / "test_reg.db"
    await init_db(db_file)
    config = Config(
        bot_token="test_token",
        admin_ids=[111222],
        db_path=db_file,
        exports_dir=tmp_path / "exports",
    )

    regions = await get_regions(config.db_path)
    reg_id = regions[0]["id"]
    hospitals = await get_hospitals_by_region(config.db_path, reg_id)
    hosp_id = hospitals[0]["id"]

    # Step 1: select region
    cb_reg = AsyncMock()
    cb_reg.data = f"reg_region:{reg_id}"
    state_mock = AsyncMock()

    await on_region_selected(cb_reg, state_mock, config)
    state_mock.update_data.assert_awaited_with(region_id=reg_id)
    state_mock.set_state.assert_awaited_with(RegistrationStates.waiting_for_hospital)
    cb_reg.message.edit_text.assert_awaited_once()
    cb_reg.answer.assert_awaited_once()

    # Step 1.5: back to regions
    cb_back = AsyncMock()
    cb_back.data = "back_to_regions"
    await on_back_to_regions(cb_back, state_mock, config)
    state_mock.set_state.assert_awaited_with(RegistrationStates.waiting_for_region)
    cb_back.message.edit_text.assert_awaited_once()

    # Step 2: select hospital
    cb_hosp = AsyncMock()
    cb_hosp.data = f"reg_hosp:{hosp_id}"
    await on_hospital_selected(cb_hosp, state_mock, config)
    state_mock.set_state.assert_awaited_with(RegistrationStates.waiting_for_name)
    cb_hosp.message.delete.assert_awaited_once()
    cb_hosp.message.answer.assert_awaited_once()

    # Step 3: enter name (too short)
    msg_short = AsyncMock()
    msg_short.text = "A"
    await on_name_entered(msg_short, state_mock)
    args, _ = msg_short.answer.call_args
    assert "tolıq kiritiń" in args[0]

    # Step 3: enter valid name
    msg_name = AsyncMock()
    msg_name.text = "Gúlshat Ernazarova"
    await on_name_entered(msg_name, state_mock)
    state_mock.update_data.assert_awaited_with(full_name="Gúlshat Ernazarova")
    state_mock.set_state.assert_awaited_with(RegistrationStates.waiting_for_phone)

    # Step 4: submit invalid phone
    state_mock.get_data.return_value = {
        "full_name": "Gúlshat Ernazarova",
        "hospital_id": hosp_id,
        "hospital_name": hospitals[0]["name"],
        "region_name": regions[0]["name"],
    }
    bot_mock = AsyncMock()
    msg_bad_phone = AsyncMock()
    msg_bad_phone.contact = None
    msg_bad_phone.text = "12345"
    await on_phone_submitted(msg_bad_phone, state_mock, bot_mock, config)
    args, _ = msg_bad_phone.answer.call_args
    assert "❌ Nomer durıs kiritilmedi" in args[0]

    # Step 4: submit valid phone via text
    msg_good_phone = AsyncMock()
    msg_good_phone.contact = None
    msg_good_phone.text = "+998 90 987 65 43"
    msg_good_phone.from_user.id = 555666
    await on_phone_submitted(msg_good_phone, state_mock, bot_mock, config)

    # State cleared
    state_mock.clear.assert_awaited_once()
    # Confirmation sent to user
    args, _ = msg_good_phone.answer.call_args
    assert "Dizimnen ótiw sorawıńız qabıllandı" in args[0]
    # Admin was notified
    bot_mock.send_message.assert_awaited_once()
    alert_args, alert_kwargs = bot_mock.send_message.call_args
    assert alert_kwargs["chat_id"] == 111222
    assert "Jańa bolnica dizimnen ótti" in alert_kwargs["text"]

    # Verify user in database
    db_user = await get_user(config.db_path, 555666)
    assert db_user is not None
    assert db_user["full_name"] == "Gúlshat Ernazarova"
    assert db_user["phone"] == "+998909876543"
    assert db_user["status"] == "pending"


@pytest.mark.asyncio
async def test_on_contact_manager():
    from bot.handlers.start import on_contact_manager
    msg = AsyncMock()
    await on_contact_manager(msg)
    args, kwargs = msg.answer.call_args
    assert "+998 95 372 01 10" in args[0]
    assert kwargs.get("reply_markup") is not None
