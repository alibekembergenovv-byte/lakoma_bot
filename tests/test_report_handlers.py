import pytest
from unittest.mock import AsyncMock
from pathlib import Path
from datetime import datetime

from bot.config import Config
from bot.database.db import init_db
from bot.database.queries import upsert_user, upsert_daily_record, get_daily_record
from bot.states.states import ReportStates
from bot.handlers.report import (
    parse_meal_count,
    format_report_summary_card,
    on_start_daily_report,
    on_view_today_submission,
    on_date_picked,
    on_breakfast_entered,
    on_lunch_entered,
    on_dinner_entered,
    on_confirm_daily_report,
    on_restart_daily_report,
    on_cancel_action,
)


def test_parse_meal_count():
    assert parse_meal_count("120") == 120
    assert parse_meal_count("0") == 0
    assert parse_meal_count(" 350 ") == 350
    assert parse_meal_count("5000") == 5000
    assert parse_meal_count("-5") is None
    assert parse_meal_count("abc") is None
    assert parse_meal_count("10000") is None
    assert parse_meal_count("") is None
    assert parse_meal_count("   ") is None
    assert parse_meal_count("12.5") is None


def test_format_report_summary_card():
    card_with_note = format_report_summary_card(
        hospital_name="Qaraózek RMO",
        date_str="2026-10-02",
        breakfast=120,
        lunch=120,
        dinner=110,
        note="Dieta awqatlar bar",
    )
    assert "Qaraózek RMO" in card_with_note
    assert "2026-10-02" in card_with_note
    assert "120" in card_with_note
    assert "110" in card_with_note
    assert "350" in card_with_note
    assert "Dieta awqatlar bar" in card_with_note
    assert "Maǵlıwmatlar durıs kiritildime?" in card_with_note

    card_without_note = format_report_summary_card(
        hospital_name="Taxtakópir RMO",
        date_str="2026-10-03",
        breakfast=50,
        lunch=60,
        dinner=55,
        note="",
    )
    assert "Taxtakópir RMO" in card_without_note
    assert "165" in card_without_note
    assert "Eskertiw" not in card_without_note


@pytest.mark.asyncio
async def test_on_start_daily_report_unapproved(tmp_path: Path):
    db_file = tmp_path / "test_report.db"
    await init_db(db_file)
    config = Config(
        bot_token="test_token",
        admin_ids=[111222],
        db_path=db_file,
        exports_dir=tmp_path / "exports",
    )

    message = AsyncMock()
    message.from_user.id = 999111
    state = AsyncMock()

    await on_start_daily_report(message, state, config)
    args, _ = message.answer.call_args
    assert "tastıyıqlanbaǵansız" in args[0]
    state.set_state.assert_not_called()


@pytest.mark.asyncio
async def test_on_start_daily_report_approved(tmp_path: Path):
    db_file = tmp_path / "test_report.db"
    await init_db(db_file)
    config = Config(
        bot_token="test_token",
        admin_ids=[111222],
        db_path=db_file,
        exports_dir=tmp_path / "exports",
    )

    user_id = 999222
    await upsert_user(
        db_path=db_file,
        telegram_id=user_id,
        full_name="Doctor Approved",
        phone="+998901234567",
        hospital_id=1,
        role="hospital_user",
        status="approved",
    )

    message = AsyncMock()
    message.from_user.id = user_id
    state = AsyncMock()

    await on_start_daily_report(message, state, config)
    state.clear.assert_awaited_once()
    state.set_state.assert_awaited_with(ReportStates.select_date)
    assert message.answer.call_count == 1
    args, kwargs = message.answer.call_args
    assert "Qaysı kún ushın" in args[0]
    assert kwargs.get("reply_markup") is not None


@pytest.mark.asyncio
async def test_on_view_today_submission_unapproved(tmp_path: Path):
    db_file = tmp_path / "test_report.db"
    await init_db(db_file)
    config = Config(
        bot_token="test_token",
        admin_ids=[111222],
        db_path=db_file,
        exports_dir=tmp_path / "exports",
    )

    message = AsyncMock()
    message.from_user.id = 888111

    await on_view_today_submission(message, config)
    args, _ = message.answer.call_args
    assert "tastıyıqlanbaǵansız" in args[0]


@pytest.mark.asyncio
async def test_on_view_today_submission_empty_and_exists(tmp_path: Path):
    db_file = tmp_path / "test_report.db"
    await init_db(db_file)
    config = Config(
        bot_token="test_token",
        admin_ids=[111222],
        db_path=db_file,
        exports_dir=tmp_path / "exports",
    )

    user_id = 888222
    await upsert_user(
        db_path=db_file,
        telegram_id=user_id,
        full_name="Hospital Nurse",
        phone="+998901234567",
        hospital_id=1,
        role="hospital_user",
        status="approved",
    )

    # 1. No record today
    today = datetime.now().strftime("%Y-%m-%d")
    msg_empty = AsyncMock()
    msg_empty.from_user.id = user_id
    await on_view_today_submission(msg_empty, config)
    args, _ = msg_empty.answer.call_args
    assert "ele maǵlıwmat kiritilmegen" in args[0]

    # 2. Existing record today
    await upsert_daily_record(
        db_path=db_file,
        hospital_id=1,
        user_id=user_id,
        report_date=today,
        breakfast=100,
        lunch=105,
        dinner=95,
        note="Barlıǵı jaqsı",
    )
    msg_exists = AsyncMock()
    msg_exists.from_user.id = user_id
    await on_view_today_submission(msg_exists, config)
    args, _ = msg_exists.answer.call_args
    assert "Búgingi kúnlik kiritilgen maǵlıwmatıńız" in args[0]
    assert "300" in args[0]
    assert "Barlıǵı jaqsı" in args[0]


@pytest.mark.asyncio
async def test_daily_report_interactive_flow(tmp_path: Path):
    db_file = tmp_path / "test_report.db"
    await init_db(db_file)
    config = Config(
        bot_token="test_token",
        admin_ids=[111222],
        db_path=db_file,
        exports_dir=tmp_path / "exports",
    )

    user_id = 777111
    await upsert_user(
        db_path=db_file,
        telegram_id=user_id,
        full_name="Report Tester",
        phone="+998907771111",
        hospital_id=1,
        role="hospital_user",
        status="approved",
    )

    state = AsyncMock()
    state_store = {}

    async def mock_update_data(**kwargs):
        state_store.update(kwargs)

    async def mock_get_data():
        return state_store

    state.update_data.side_effect = mock_update_data
    state.get_data.side_effect = mock_get_data

    # 1. on_date_picked
    cb_date = AsyncMock()
    cb_date.data = "set_date:2026-10-05"
    await on_date_picked(cb_date, state)
    assert state_store["report_date"] == "2026-10-05"
    state.set_state.assert_awaited_with(ReportStates.waiting_for_breakfast)
    cb_date.message.delete.assert_awaited_once()
    cb_date.message.answer.assert_awaited_once()
    args, _ = cb_date.message.answer.call_args
    assert "2026-10-05" in args[0]
    assert "Azanǵı awqatqa" in args[0]
    cb_date.answer.assert_awaited_once()

    # 2. on_breakfast_entered - invalid then valid
    msg_br_bad = AsyncMock()
    msg_br_bad.text = "not_a_number"
    await on_breakfast_entered(msg_br_bad, state)
    args, _ = msg_br_bad.answer.call_args
    assert "❌ Iltimas, durıs san kiritiń" in args[0]

    msg_br_good = AsyncMock()
    msg_br_good.text = "135"
    await on_breakfast_entered(msg_br_good, state)
    assert state_store["breakfast"] == 135
    state.set_state.assert_awaited_with(ReportStates.waiting_for_lunch)
    args, _ = msg_br_good.answer.call_args
    assert "Túslik (obet) ushın" in args[0]

    # 3. on_lunch_entered - invalid then valid
    msg_lu_bad = AsyncMock()
    msg_lu_bad.text = "-1"
    await on_lunch_entered(msg_lu_bad, state)
    args, _ = msg_lu_bad.answer.call_args
    assert "❌ Iltimas, durıs san kiritiń" in args[0]

    msg_lu_good = AsyncMock()
    msg_lu_good.text = "140"
    await on_lunch_entered(msg_lu_good, state)
    assert state_store["lunch"] == 140
    state.set_state.assert_awaited_with(ReportStates.waiting_for_dinner)
    args, _ = msg_lu_good.answer.call_args
    assert "Keshki awqat ushın" in args[0]

    # 4. on_dinner_entered - invalid then valid
    msg_di_bad = AsyncMock()
    msg_di_bad.text = "99999"
    msg_di_bad.from_user.id = user_id
    await on_dinner_entered(msg_di_bad, state, config)
    args, _ = msg_di_bad.answer.call_args
    assert "❌ Iltimas, durıs san kiritiń" in args[0]

    msg_di_good = AsyncMock()
    msg_di_good.text = "125"
    msg_di_good.from_user.id = user_id
    await on_dinner_entered(msg_di_good, state, config)
    assert state_store["dinner"] == 125
    state.set_state.assert_awaited_with(ReportStates.confirm_report)
    args, kwargs = msg_di_good.answer.call_args
    assert "400" in args[0]  # 135 + 140 + 125 = 400
    assert "Maǵlıwmatlar durıs kiritildime?" in args[0]
    assert kwargs.get("reply_markup") is not None

    # 5. on_restart_daily_report
    cb_restart = AsyncMock()
    cb_restart.data = "restart_daily_report"
    await on_restart_daily_report(cb_restart, state)
    state.set_state.assert_awaited_with(ReportStates.select_date)
    cb_restart.message.edit_text.assert_awaited_once()
    cb_restart.answer.assert_awaited_once()

    # 6. on_confirm_daily_report
    cb_confirm = AsyncMock()
    cb_confirm.data = "confirm_daily_report"
    cb_confirm.from_user.id = user_id
    await on_confirm_daily_report(cb_confirm, state, config)

    state.clear.assert_awaited_once()
    cb_confirm.message.edit_text.assert_awaited_once()
    args, _ = cb_confirm.message.edit_text.call_args
    assert "bazaǵa jazıldı" in args[0]
    cb_confirm.answer.assert_awaited_once()

    # Verify database record
    rec = await get_daily_record(config.db_path, 1, "2026-10-05")
    assert rec is not None
    assert rec["breakfast_count"] == 135
    assert rec["lunch_count"] == 140
    assert rec["dinner_count"] == 125
    assert rec["total_daily"] == 400


@pytest.mark.asyncio
async def test_on_cancel_action():
    state = AsyncMock()
    cb_cancel = AsyncMock()
    cb_cancel.data = "cancel_action"

    await on_cancel_action(cb_cancel, state)
    state.clear.assert_awaited_once()
    cb_cancel.message.delete.assert_awaited_once()
    cb_cancel.answer.assert_awaited_with("Biykar etildi")
