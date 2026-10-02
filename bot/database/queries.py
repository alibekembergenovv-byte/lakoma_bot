from pathlib import Path
import aiosqlite

async def get_regions(db_path: Path) -> list[dict]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute("SELECT id, name FROM regions ORDER BY id ASC;") as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_hospitals_by_region(db_path: Path, region_id: int) -> list[dict]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            "SELECT id, region_id, name FROM hospitals WHERE region_id = ? ORDER BY id ASC;",
            (region_id,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_all_hospitals(db_path: Path) -> list[dict]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT h.id, h.name, h.region_id, r.name as region_name
            FROM hospitals h
            JOIN regions r ON h.region_id = r.id
            ORDER BY h.id ASC;
            """
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_hospital_by_id(db_path: Path, hospital_id: int) -> dict | None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT h.id, h.name as hospital_name, h.region_id, r.name as region_name
            FROM hospitals h
            JOIN regions r ON h.region_id = r.id
            WHERE h.id = ?;
            """,
            (hospital_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def upsert_user(
    db_path: Path,
    telegram_id: int,
    full_name: str,
    phone: str,
    hospital_id: int | None,
    role: str = 'hospital_user',
    status: str = 'pending'
) -> None:
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO users (telegram_id, full_name, phone, hospital_id, role, status)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                full_name = excluded.full_name,
                phone = excluded.phone,
                hospital_id = excluded.hospital_id,
                role = excluded.role,
                status = excluded.status;
            """,
            (telegram_id, full_name, phone, hospital_id, role, status)
        )
        await db.commit()

async def get_user(db_path: Path, telegram_id: int) -> dict | None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT u.telegram_id, u.full_name, u.phone, u.hospital_id, u.role, u.status, u.created_at,
                   h.name as hospital_name, r.name as region_name
            FROM users u
            LEFT JOIN hospitals h ON u.hospital_id = h.id
            LEFT JOIN regions r ON h.region_id = r.id
            WHERE u.telegram_id = ?;
            """,
            (telegram_id,)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def set_user_status(db_path: Path, telegram_id: int, status: str) -> bool:
    async with aiosqlite.connect(db_path) as db:
        cur = await db.execute(
            "UPDATE users SET status = ? WHERE telegram_id = ?;",
            (status, telegram_id)
        )
        await db.commit()
        return cur.rowcount > 0

async def get_pending_users(db_path: Path) -> list[dict]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT u.telegram_id, u.full_name, u.phone, u.hospital_id, u.created_at,
                   h.name as hospital_name, r.name as region_name
            FROM users u
            LEFT JOIN hospitals h ON u.hospital_id = h.id
            LEFT JOIN regions r ON h.region_id = r.id
            WHERE u.status = 'pending' AND u.role = 'hospital_user'
            ORDER BY u.created_at ASC;
            """
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def upsert_daily_record(
    db_path: Path,
    hospital_id: int,
    user_id: int,
    report_date: str,
    breakfast: int,
    lunch: int,
    dinner: int,
    note: str = ""
) -> None:
    total = breakfast + lunch + dinner
    async with aiosqlite.connect(db_path) as db:
        await db.execute(
            """
            INSERT INTO daily_records (hospital_id, user_id, report_date, breakfast_count, lunch_count, dinner_count, total_daily, note, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(hospital_id, report_date) DO UPDATE SET
                user_id = excluded.user_id,
                breakfast_count = excluded.breakfast_count,
                lunch_count = excluded.lunch_count,
                dinner_count = excluded.dinner_count,
                total_daily = excluded.total_daily,
                note = excluded.note,
                updated_at = CURRENT_TIMESTAMP;
            """,
            (hospital_id, user_id, report_date, breakfast, lunch, dinner, total, note)
        )
        await db.commit()

async def get_daily_record(db_path: Path, hospital_id: int, report_date: str) -> dict | None:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT dr.*, h.name as hospital_name, r.name as region_name, u.full_name as user_name, u.phone as user_phone
            FROM daily_records dr
            JOIN hospitals h ON dr.hospital_id = h.id
            JOIN regions r ON h.region_id = r.id
            LEFT JOIN users u ON dr.user_id = u.telegram_id
            WHERE dr.hospital_id = ? AND dr.report_date = ?;
            """,
            (hospital_id, report_date)
        ) as cursor:
            row = await cursor.fetchone()
            return dict(row) if row else None

async def get_daily_summary(db_path: Path, report_date: str) -> dict:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT dr.hospital_id, dr.report_date, dr.breakfast_count, dr.lunch_count, dr.dinner_count,
                   dr.total_daily, dr.updated_at, dr.note,
                   h.name as hospital_name, r.name as region_name,
                   u.full_name as user_name, u.phone as user_phone
            FROM daily_records dr
            JOIN hospitals h ON dr.hospital_id = h.id
            JOIN regions r ON h.region_id = r.id
            LEFT JOIN users u ON dr.user_id = u.telegram_id
            WHERE dr.report_date = ?
            ORDER BY r.name ASC, h.name ASC;
            """,
            (report_date,)
        ) as cursor:
            rows = await cursor.fetchall()
            items = [dict(r) for r in rows]

        total_breakfast = sum(item["breakfast_count"] for item in items)
        total_lunch = sum(item["lunch_count"] for item in items)
        total_dinner = sum(item["dinner_count"] for item in items)
        total_all = sum(item["total_daily"] for item in items)

        # Count total approved active hospitals
        async with db.execute("SELECT COUNT(*) FROM hospitals;") as cur_hosp:
            total_hospitals = (await cur_hosp.fetchone())[0]

        return {
            "date": report_date,
            "total_hospitals": total_hospitals,
            "submitted_hospitals": len(items),
            "total_breakfast": total_breakfast,
            "total_lunch": total_lunch,
            "total_dinner": total_dinner,
            "total_all": total_all,
            "items": items
        }

async def get_missing_hospitals(db_path: Path, report_date: str) -> list[dict]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT h.id, h.name as hospital_name, r.name as region_name,
                   u.telegram_id as user_telegram_id, u.full_name as user_name, u.phone as user_phone
            FROM hospitals h
            JOIN regions r ON h.region_id = r.id
            LEFT JOIN users u ON u.hospital_id = h.id AND u.status = 'approved'
            WHERE h.id NOT IN (
                SELECT hospital_id FROM daily_records WHERE report_date = ?
            )
            ORDER BY r.name ASC, h.name ASC;
            """,
            (report_date,)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]

async def get_records_for_period(db_path: Path, start_date: str, end_date: str) -> list[dict]:
    async with aiosqlite.connect(db_path) as db:
        db.row_factory = aiosqlite.Row
        async with db.execute(
            """
            SELECT dr.report_date, dr.breakfast_count, dr.lunch_count, dr.dinner_count,
                   dr.total_daily, dr.note, dr.updated_at,
                   h.name as hospital_name, r.name as region_name,
                   u.full_name as user_name, u.phone as user_phone
            FROM daily_records dr
            JOIN hospitals h ON dr.hospital_id = h.id
            JOIN regions r ON h.region_id = r.id
            LEFT JOIN users u ON dr.user_id = u.telegram_id
            WHERE dr.report_date BETWEEN ? AND ?
            ORDER BY dr.report_date DESC, r.name ASC, h.name ASC;
            """,
            (start_date, end_date)
        ) as cursor:
            rows = await cursor.fetchall()
            return [dict(r) for r in rows]
