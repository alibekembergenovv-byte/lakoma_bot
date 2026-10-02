import pytest
from pathlib import Path
import openpyxl

from bot.database.db import init_db
from bot.database.queries import (
    get_regions,
    get_hospitals_by_region,
    upsert_user,
    get_user,
    set_user_status,
    upsert_daily_record,
    get_daily_summary,
    get_missing_hospitals,
)
from bot.services.excel_service import generate_daily_excel


@pytest.mark.asyncio
async def test_full_business_workflow(tmp_path: Path):
    db_file = tmp_path / "e2e_lakoma.db"
    await init_db(db_file)

    # 1. Hospital selects Region and Hospital
    regions = await get_regions(db_file)
    assert len(regions) > 0
    qaraozek = next(r for r in regions if "Qaraózek" in r["name"])
    hospitals = await get_hospitals_by_region(db_file, qaraozek["id"])
    assert len(hospitals) > 0
    hosp = hospitals[0]

    # 2. Hospital submits registration
    nurse_tg_id = 7771234
    await upsert_user(
        db_path=db_file,
        telegram_id=nurse_tg_id,
        full_name="Aynura Sarsenbaeva",
        phone="+998901112233",
        hospital_id=hosp["id"],
        role="hospital_user",
        status="pending",
    )

    nurse = await get_user(db_file, nurse_tg_id)
    assert nurse is not None
    assert nurse["status"] == "pending"
    assert nurse["full_name"] == "Aynura Sarsenbaeva"
    assert nurse["hospital_name"] == hosp["name"]

    # 3. Admin approves registration
    success = await set_user_status(db_file, nurse_tg_id, "approved")
    assert success is True
    nurse = await get_user(db_file, nurse_tg_id)
    assert nurse["status"] == "approved"

    # 4. Nurse reports daily headcounts for today
    today = "2026-10-02"
    await upsert_daily_record(
        db_path=db_file,
        hospital_id=hosp["id"],
        user_id=nurse_tg_id,
        report_date=today,
        breakfast=120,
        lunch=120,
        dinner=110,
        note="Barlıq bolimler tolıq",
    )

    # 5. Lakoma Admin inspects daily summary
    summary = await get_daily_summary(db_file, today)
    assert summary["date"] == today
    assert summary["total_breakfast"] == 120
    assert summary["total_lunch"] == 120
    assert summary["total_dinner"] == 110
    assert summary["total_all"] == 350
    assert summary["submitted_hospitals"] == 1
    assert len(summary["items"]) == 1
    assert summary["items"][0]["hospital_name"] == hosp["name"]
    assert summary["items"][0]["note"] == "Barlıq bolimler tolıq"

    # 6. Check missing hospitals
    missing = await get_missing_hospitals(db_file, today)
    assert not any(m["id"] == hosp["id"] for m in missing)
    assert len(missing) > 0  # other hospitals haven't submitted yet

    # 7. Generate Excel file and verify content
    excel_path = tmp_path / "e2e_report.xlsx"
    out = generate_daily_excel(summary, excel_path)
    assert out.exists()
    assert out.stat().st_size > 3000

    # Inspect generated Excel with openpyxl
    wb = openpyxl.load_workbook(out)
    ws = wb.active
    assert ws is not None
    assert "LAKOMA" in ws["A1"].value
    
    # Check that hospital name and totals appear in the sheet
    found_hosp = False
    for row in ws.iter_rows(values_only=True):
        if row and any(hosp["name"] in str(cell) for cell in row if cell is not None):
            found_hosp = True
            break
    assert found_hosp is True
