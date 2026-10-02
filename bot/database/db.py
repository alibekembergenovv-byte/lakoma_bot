from pathlib import Path
import aiosqlite
from bot.database.seed_data import INITIAL_REGIONS_AND_HOSPITALS

async def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(db_path) as db:
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA foreign_keys=ON;")
        
        await db.execute("""
        CREATE TABLE IF NOT EXISTS regions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );
        """)
        
        await db.execute("""
        CREATE TABLE IF NOT EXISTS hospitals (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            region_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            FOREIGN KEY (region_id) REFERENCES regions(id) ON DELETE CASCADE
        );
        """)
        
        await db.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            full_name TEXT NOT NULL,
            phone TEXT,
            hospital_id INTEGER,
            role TEXT NOT NULL DEFAULT 'hospital_user',
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE SET NULL
        );
        """)
        
        await db.execute("""
        CREATE TABLE IF NOT EXISTS daily_records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            hospital_id INTEGER NOT NULL,
            user_id INTEGER NOT NULL,
            report_date DATE NOT NULL,
            breakfast_count INTEGER NOT NULL DEFAULT 0,
            lunch_count INTEGER NOT NULL DEFAULT 0,
            dinner_count INTEGER NOT NULL DEFAULT 0,
            total_daily INTEGER NOT NULL DEFAULT 0,
            note TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(hospital_id, report_date),
            FOREIGN KEY (hospital_id) REFERENCES hospitals(id) ON DELETE CASCADE,
            FOREIGN KEY (user_id) REFERENCES users(telegram_id)
        );
        """)
        await db.commit()

        # Seed regions and hospitals if empty
        cursor = await db.execute("SELECT COUNT(*) FROM regions;")
        count = (await cursor.fetchone())[0]
        if count == 0:
            for region_name, hosp_list in INITIAL_REGIONS_AND_HOSPITALS.items():
                cur = await db.execute("INSERT INTO regions (name) VALUES (?);", (region_name,))
                region_id = cur.lastrowid
                for hosp_name in hosp_list:
                    await db.execute(
                        "INSERT INTO hospitals (region_id, name) VALUES (?, ?);",
                        (region_id, hosp_name)
                    )
            await db.commit()
