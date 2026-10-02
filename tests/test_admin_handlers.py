import pytest
from unittest.mock import AsyncMock, patch
from pathlib import Path
from datetime import datetime

from bot.config import Config
from bot.database.db import init_db
from bot.database.queries import upsert_user, upsert_daily_record, get_user
from bot.handlers.admin import (
    is_admin,
    format_admin_summary_text,
    on_admin_today_summary,
    on_admin_missing_list,
    on_broadcast_reminders,
    on_admin_pending_users,
    on_approve_user,
    on_reject_user,
    on_admin_excel_menu,
    on_excel_day_download,
    on_excel_month_download,
)


def test_is_admin():
    cfg = Config(
        bot_token="fake_token",
        admin_ids=[12345, 67890],
        db_path=Path("dummy.db"),
        exports_dir=Path("dummy_exports"),
    )
    assert is_admin(12345, cfg) is True
    assert is_admin(67890, cfg) is True
    assert is_admin(99999, cfg) is False


def test_format_admin_summary_text():
    # 1. Summary with submitted items
    summary_data = {
        "date": "2026-10-02",
        "total_hospitals": 16,
        "submitted_hospitals": 2,
        "total_breakfast": 240,
        "total_lunch": 250,
        "total_dinner": 230,
        "total_all": 720,
        "items": [
            {
                "region_name": "Qaraózek",
                "hospital_name": "Qaraózek RMO",
                "breakfast_count": 120,
                "lunch_count": 125,
                "dinner_count": 115,
                "total_daily": 360,
            }
        ],
    }
    text = format_admin_summary_text(summary_data)
    assert "2026-10-02" in text
    assert "240" in text
    assert "720" in text
    assert "Qaraózek RMO" in text
    assert "2 / 16" in text

    # 2. Empty summary items
    empty_summary = {
        "date": "2026-10-02",
        "total_hospitals": 16,
        "submitted_hospitals": 0,
        "total_breakfast": 0,
        "total_lunch": 0,
        "total_dinner": 0,
        "total_all": 0,
        "items": [],
    }
    empty_text = format_admin_summary_text(empty_summary)
    assert "Ele hesh qaysı bolnica maǵlıwmat kiritpedi" in empty_text


@pytest.mark.asyncio
async def test_on_admin_today_summary(tmp_path: Path):
    db_file = tmp_path / "test_admin.db"
    await init_db(db_file)
    admin_id = 111222
    non_admin_id = 999888
    config = Config(
        bot_token="test_token",
        admin_ids=[admin_id],
        db_path=db_file,
        exports_dir=tmp_path / "exports",
    )

    # 1. Non-admin calls
    msg_non_admin = AsyncMock()
    msg_non_admin.from_user.id = non_admin_id
    await on_admin_today_summary(msg_non_admin, config)
    msg_non_admin.answer.assert_not_called()

    # 2. Admin calls
    today = datetime.now().strftime("%Y-%m-%d")
    await upsert_daily_record(
        db_path=db_file,
        hospital_id=1,
        user_id=1001,
        report_date=today,
        breakfast=100,
        lunch=100,
        dinner=100,
    )

    msg_admin = AsyncMock()
    msg_admin.from_user.id = admin_id
    await on_admin_today_summary(msg_admin, config)
    assert msg_admin.answer.call_count == 1
    args, kwargs = msg_admin.answer.call_args
    assert today in args[0]
    assert "300" in args[0]
    assert kwargs.get("parse_mode") == "HTML"


@pytest.mark.asyncio
async def test_on_admin_missing_list(tmp_path: Path):
    db_file = tmp_path / "test_admin.db"
    await init_db(db_file)
    admin_id = 111222
    config = Config(
        bot_token="test_token",
        admin_ids=[admin_id],
        db_path=db_file,
        exports_dir=tmp_path / "exports",
    )

    # 1. Non-admin
    msg_non_admin = AsyncMock()
    msg_non_admin.from_user.id = 999888
    await on_admin_missing_list(msg_non_admin, config)
    msg_non_admin.answer.assert_not_called()

    # 2. Admin with missing hospitals
    msg_admin = AsyncMock()
    msg_admin.from_user.id = admin_id
    await on_admin_missing_list(msg_admin, config)
    args, kwargs = msg_admin.answer.call_args
    assert "san kiritpegen bolnicalar" in args[0]
    assert kwargs.get("parse_mode") == "HTML"

    # 3. Admin when all hospitals submitted
    today = datetime.now().strftime("%Y-%m-%d")
    # Mark all hospitals as submitted
    import aiosqlite

    async with aiosqlite.connect(db_file) as db:
        async with db.execute("SELECT id FROM hospitals") as cursor:
            hosp_ids = [row[0] for row in await cursor.fetchall()]
        for hid in hosp_ids:
            await db.execute(
                """
                INSERT INTO daily_records (hospital_id, user_id, report_date, breakfast_count, lunch_count, dinner_count, total_daily)
                VALUES (?, 1, ?, 10, 10, 10, 30);
                """,
                (hid, today),
            )
        await db.commit()

    msg_all_done = AsyncMock()
    msg_all_done.from_user.id = admin_id
    await on_admin_missing_list(msg_all_done, config)
    args, _ = msg_all_done.answer.call_args
    assert "Barlıq bolnicalar" in args[0]


@pytest.mark.asyncio
async def test_on_broadcast_reminders(tmp_path: Path):
    db_file = tmp_path / "test_admin.db"
    await init_db(db_file)
    admin_id = 111222
    config = Config(
        bot_token="test_token",
        admin_ids=[admin_id],
        db_path=db_file,
        exports_dir=tmp_path / "exports",
    )

    # 1. Non-admin
    msg_non_admin = AsyncMock()
    msg_non_admin.from_user.id = 999888
    bot_mock = AsyncMock()
    await on_broadcast_reminders(msg_non_admin, bot_mock, config)
    bot_mock.send_message.assert_not_called()
    msg_non_admin.answer.assert_not_called()

    # 2. Admin with approved users for missing hospitals
    user1_id = 555111
    user2_id = 555222
    await upsert_user(
        db_path=db_file,
        telegram_id=user1_id,
        full_name="Doctor One",
        phone="+998901111111",
        hospital_id=1,
        role="hospital_user",
        status="approved",
    )
    await upsert_user(
        db_path=db_file,
        telegram_id=user2_id,
        full_name="Doctor Two",
        phone="+998902222222",
        hospital_id=2,
        role="hospital_user",
        status="approved",
    )

    msg_admin = AsyncMock()
    msg_admin.from_user.id = admin_id

    # Test error handling when one message fails
    async def mock_send(chat_id, text, **kwargs):
        if chat_id == user2_id:
            raise Exception("Telegram blocked")
        return True

    bot_mock.send_message.side_effect = mock_send

    await on_broadcast_reminders(msg_admin, bot_mock, config)

    # user1 succeeded, user2 failed, so sent_count == 1
    assert msg_admin.answer.call_count == 1
    args, kwargs = msg_admin.answer.call_args
    assert "1" in args[0]
    assert "esletpe jiberildi" in args[0]


@pytest.mark.asyncio
async def test_on_admin_pending_users(tmp_path: Path):
    db_file = tmp_path / "test_admin.db"
    await init_db(db_file)
    admin_id = 111222
    config = Config(
        bot_token="test_token",
        admin_ids=[admin_id],
        db_path=db_file,
        exports_dir=tmp_path / "exports",
    )

    # 1. Non-admin
    msg_non_admin = AsyncMock()
    msg_non_admin.from_user.id = 999888
    await on_admin_pending_users(msg_non_admin, config)
    msg_non_admin.answer.assert_not_called()

    # 2. Admin with no pending users
    msg_admin = AsyncMock()
    msg_admin.from_user.id = admin_id
    await on_admin_pending_users(msg_admin, config)
    args, _ = msg_admin.answer.call_args
    assert "jańa bolnica joq" in args[0]

    # 3. Admin with pending users
    pending_user_id = 777111
    await upsert_user(
        db_path=db_file,
        telegram_id=pending_user_id,
        full_name="Gulnara Joldasova",
        phone="+998913334455",
        hospital_id=1,
        role="hospital_user",
        status="pending",
    )

    msg_pending = AsyncMock()
    msg_pending.from_user.id = admin_id
    await on_admin_pending_users(msg_pending, config)
    assert msg_pending.answer.call_count == 1
    args, kwargs = msg_pending.answer.call_args
    assert "Gulnara Joldasova" in args[0]
    assert kwargs.get("reply_markup") is not None


@pytest.mark.asyncio
async def test_on_approve_user(tmp_path: Path):
    db_file = tmp_path / "test_admin.db"
    await init_db(db_file)
    admin_id = 111222
    config = Config(
        bot_token="test_token",
        admin_ids=[admin_id],
        db_path=db_file,
        exports_dir=tmp_path / "exports",
    )

    user_id = 888333
    await upsert_user(
        db_path=db_file,
        telegram_id=user_id,
        full_name="Pending Doctor",
        phone="+998907778899",
        hospital_id=1,
        role="hospital_user",
        status="pending",
    )

    bot_mock = AsyncMock()

    # 1. Non-admin tries to approve
    cb_non_admin = AsyncMock()
    cb_non_admin.from_user.id = 999888
    cb_non_admin.data = f"mod_approve:{user_id}"
    await on_approve_user(cb_non_admin, bot_mock, config)
    cb_non_admin.answer.assert_called_with("Ruxsat joq!", show_alert=True)
    # Check user is still pending
    u = await get_user(db_file, user_id)
    assert u["status"] == "pending"

    # 2. Admin approves
    cb_admin = AsyncMock()
    cb_admin.from_user.id = admin_id
    cb_admin.data = f"mod_approve:{user_id}"
    cb_admin.message.text = "🆕 Kútilip atırǵan dizim: Pending Doctor"
    await on_approve_user(cb_admin, bot_mock, config)

    u = await get_user(db_file, user_id)
    assert u["status"] == "approved"
    cb_admin.message.edit_text.assert_called_once()
    assert "Tastıyıqlandı" in cb_admin.message.edit_text.call_args[0][0]
    cb_admin.answer.assert_called_with("Tastıyıqlandı!")
    bot_mock.send_message.assert_called_once()
    assert bot_mock.send_message.call_args[1]["chat_id"] == user_id


@pytest.mark.asyncio
async def test_on_reject_user(tmp_path: Path):
    db_file = tmp_path / "test_admin.db"
    await init_db(db_file)
    admin_id = 111222
    config = Config(
        bot_token="test_token",
        admin_ids=[admin_id],
        db_path=db_file,
        exports_dir=tmp_path / "exports",
    )

    user_id = 888444
    await upsert_user(
        db_path=db_file,
        telegram_id=user_id,
        full_name="To Be Rejected",
        phone="+998907778899",
        hospital_id=1,
        role="hospital_user",
        status="pending",
    )

    bot_mock = AsyncMock()

    # 1. Non-admin tries to reject
    cb_non_admin = AsyncMock()
    cb_non_admin.from_user.id = 999888
    cb_non_admin.data = f"mod_reject:{user_id}"
    await on_reject_user(cb_non_admin, bot_mock, config)
    cb_non_admin.answer.assert_called_with("Ruxsat joq!", show_alert=True)
    u = await get_user(db_file, user_id)
    assert u["status"] == "pending"

    # 2. Admin rejects
    cb_admin = AsyncMock()
    cb_admin.from_user.id = admin_id
    cb_admin.data = f"mod_reject:{user_id}"
    cb_admin.message.text = "🆕 Kútilip atırǵan dizim: To Be Rejected"
    await on_reject_user(cb_admin, bot_mock, config)

    u = await get_user(db_file, user_id)
    assert u["status"] == "rejected"
    cb_admin.message.edit_text.assert_called_once()
    assert "Biykar etildi" in cb_admin.message.edit_text.call_args[0][0]
    cb_admin.answer.assert_called_with("Biykar etildi!")
    bot_mock.send_message.assert_called_once()
    assert bot_mock.send_message.call_args[1]["chat_id"] == user_id


@pytest.mark.asyncio
async def test_on_admin_excel_menu():
    admin_id = 111222
    config = Config(
        bot_token="test_token",
        admin_ids=[admin_id],
        db_path=Path("dummy.db"),
        exports_dir=Path("dummy_exports"),
    )

    # 1. Non-admin
    msg_non_admin = AsyncMock()
    msg_non_admin.from_user.id = 999888
    await on_admin_excel_menu(msg_non_admin, config)
    msg_non_admin.answer.assert_not_called()

    # 2. Admin
    msg_admin = AsyncMock()
    msg_admin.from_user.id = admin_id
    await on_admin_excel_menu(msg_admin, config)
    assert msg_admin.answer.call_count == 1
    args, kwargs = msg_admin.answer.call_args
    assert "Excel esabat kerek" in args[0]
    assert kwargs.get("reply_markup") is not None


@pytest.mark.asyncio
async def test_on_excel_day_download(tmp_path: Path):
    db_file = tmp_path / "test_admin.db"
    await init_db(db_file)
    admin_id = 111222
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    config = Config(
        bot_token="test_token",
        admin_ids=[admin_id],
        db_path=db_file,
        exports_dir=exports_dir,
    )

    # 1. Non-admin
    cb_non_admin = AsyncMock()
    cb_non_admin.from_user.id = 999888
    cb_non_admin.data = "excel_day:2026-10-02"
    await on_excel_day_download(cb_non_admin, config)
    cb_non_admin.answer.assert_called_with("Ruxsat joq!", show_alert=True)
    cb_non_admin.message.answer_document.assert_not_called()

    # 2. Admin
    cb_admin = AsyncMock()
    cb_admin.from_user.id = admin_id
    cb_admin.data = "excel_day:2026-10-02"
    await on_excel_day_download(cb_admin, config)

    assert cb_admin.message.answer_document.call_count == 1
    args, kwargs = cb_admin.message.answer_document.call_args
    assert "2026-10-02" in kwargs.get("caption", "")
    cb_admin.answer.assert_called_once()
    assert (exports_dir / "lakoma_daily_2026-10-02.xlsx").exists()


@pytest.mark.asyncio
async def test_on_excel_month_download(tmp_path: Path):
    db_file = tmp_path / "test_admin.db"
    await init_db(db_file)
    admin_id = 111222
    exports_dir = tmp_path / "exports"
    exports_dir.mkdir(parents=True, exist_ok=True)
    config = Config(
        bot_token="test_token",
        admin_ids=[admin_id],
        db_path=db_file,
        exports_dir=exports_dir,
    )

    # 1. Non-admin
    cb_non_admin = AsyncMock()
    cb_non_admin.from_user.id = 999888
    cb_non_admin.data = "excel_current_month"
    await on_excel_month_download(cb_non_admin, config)
    cb_non_admin.answer.assert_called_with("Ruxsat joq!", show_alert=True)
    cb_non_admin.message.answer_document.assert_not_called()

    # 2. Admin
    cb_admin = AsyncMock()
    cb_admin.from_user.id = admin_id
    cb_admin.data = "excel_current_month"
    await on_excel_month_download(cb_admin, config)

    assert cb_admin.message.answer_document.call_count == 1
    cb_admin.answer.assert_called_once()
    month_str = datetime.now().strftime("%Y-%m")
    assert (exports_dir / f"lakoma_monthly_{month_str}.xlsx").exists()
