import pytest
from pathlib import Path
from bot.database.db import init_db
from bot.database.queries import (
    get_regions,
    get_hospitals_by_region,
    get_hospital_by_id,
    upsert_user,
    get_user,
    set_user_status,
    get_pending_users,
    upsert_daily_record,
    get_daily_record,
    get_daily_summary,
    get_missing_hospitals,
    get_records_for_period,
)

@pytest.mark.asyncio
async def test_db_lifecycle_and_queries(tmp_path: Path):
    db_file = tmp_path / "test_lakoma.db"
    
    # 1. Initialize DB and verify WAL & seeds
    await init_db(db_file)
    
    # Verify WAL journal mode
    import aiosqlite
    async with aiosqlite.connect(db_file) as db:
        cur = await db.execute("PRAGMA journal_mode;")
        journal_mode = (await cur.fetchone())[0]
        assert journal_mode.lower() == "wal"

    # Idempotent init_db check (running again should not duplicate data)
    await init_db(db_file)

    # 2. Check regions and hospitals seeded
    regions = await get_regions(db_file)
    assert len(regions) > 0
    first_reg = regions[0]
    assert "id" in first_reg
    assert "name" in first_reg

    hospitals = await get_hospitals_by_region(db_file, first_reg["id"])
    assert len(hospitals) > 0
    hosp = hospitals[0]
    assert hosp["region_id"] == first_reg["id"]

    # 3. get_hospital_by_id
    hosp_info = await get_hospital_by_id(db_file, hosp["id"])
    assert hosp_info is not None
    assert hosp_info["id"] == hosp["id"]
    assert hosp_info["hospital_name"] == hosp["name"]
    assert hosp_info["region_name"] == first_reg["name"]

    non_existent_hosp = await get_hospital_by_id(db_file, 999999)
    assert non_existent_hosp is None

    # 4. User operations (upsert, get, pending, approve)
    user_id = 999888
    await upsert_user(
        db_path=db_file,
        telegram_id=user_id,
        full_name="Azamat Nuratdinov",
        phone="+998901234567",
        hospital_id=hosp["id"],
        role="hospital_user",
        status="pending"
    )
    user = await get_user(db_file, user_id)
    assert user is not None
    assert user["status"] == "pending"
    assert user["full_name"] == "Azamat Nuratdinov"
    assert user["hospital_name"] == hosp["name"]
    assert user["region_name"] == first_reg["name"]

    # Pending list
    pending = await get_pending_users(db_file)
    assert any(u["telegram_id"] == user_id for u in pending)

    # Approve user
    ok = await set_user_status(db_file, user_id, "approved")
    assert ok is True
    user = await get_user(db_file, user_id)
    assert user["status"] == "approved"

    # Non-existent user status update
    failed_status = await set_user_status(db_file, 123454321, "approved")
    assert failed_status is False

    # 5. Daily record submission (upsert, get)
    test_date = "2026-10-02"
    await upsert_daily_record(
        db_path=db_file,
        hospital_id=hosp["id"],
        user_id=user_id,
        report_date=test_date,
        breakfast=120,
        lunch=130,
        dinner=110,
        note="Normal rejim"
    )

    record = await get_daily_record(db_file, hosp["id"], test_date)
    assert record is not None
    assert record["breakfast_count"] == 120
    assert record["lunch_count"] == 130
    assert record["dinner_count"] == 110
    assert record["total_daily"] == 360
    assert record["note"] == "Normal rejim"
    assert record["hospital_name"] == hosp["name"]
    assert record["user_name"] == "Azamat Nuratdinov"

    # Update record (upsert)
    await upsert_daily_record(
        db_path=db_file,
        hospital_id=hosp["id"],
        user_id=user_id,
        report_date=test_date,
        breakfast=125,
        lunch=130,
        dinner=110,
        note="Jańalandı"
    )
    record = await get_daily_record(db_file, hosp["id"], test_date)
    assert record["breakfast_count"] == 125
    assert record["total_daily"] == 365
    assert record["note"] == "Jańalandı"

    # Non-existent daily record
    missing_record = await get_daily_record(db_file, hosp["id"], "2020-01-01")
    assert missing_record is None

    # 6. Daily summary
    summary = await get_daily_summary(db_file, test_date)
    assert summary["date"] == test_date
    assert summary["total_breakfast"] == 125
    assert summary["total_lunch"] == 130
    assert summary["total_dinner"] == 110
    assert summary["total_all"] == 365
    assert summary["submitted_hospitals"] == 1
    assert len(summary["items"]) == 1
    assert summary["total_hospitals"] == 8

    # 7. Missing hospitals
    missing = await get_missing_hospitals(db_file, test_date)
    assert not any(m["id"] == hosp["id"] for m in missing)
    assert len(missing) == summary["total_hospitals"] - 1

    # 8. Records for period
    records_period = await get_records_for_period(db_file, "2026-10-01", "2026-10-03")
    assert len(records_period) == 1
    assert records_period[0]["total_daily"] == 365
    assert records_period[0]["hospital_name"] == hosp["name"]

    # Outside period
    records_outside = await get_records_for_period(db_file, "2026-09-01", "2026-09-30")
    assert len(records_outside) == 0
