import os
from dataclasses import dataclass
from pathlib import Path
from dotenv import load_dotenv

@dataclass
class Config:
    bot_token: str
    admin_ids: list[int]
    db_path: Path
    exports_dir: Path

def load_config(env_file: str | None = None) -> Config:
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    token = os.getenv("BOT_TOKEN", "")
    admin_ids_raw = os.getenv("ADMIN_IDS", "")
    admin_ids = [
        int(x.strip()) for x in admin_ids_raw.split(",") if x.strip().isdigit()
    ]
    
    base_dir = Path(__file__).resolve().parent.parent
    db_env = Path(os.getenv("DB_PATH", "data/lakoma.db"))
    db_path = db_env if db_env.is_absolute() else base_dir / db_env

    exports_env = Path(os.getenv("EXPORTS_DIR", "exports"))
    exports_dir = exports_env if exports_env.is_absolute() else base_dir / exports_env
    
    db_path.parent.mkdir(parents=True, exist_ok=True)
    exports_dir.mkdir(parents=True, exist_ok=True)

    return Config(
        bot_token=token,
        admin_ids=admin_ids,
        db_path=db_path,
        exports_dir=exports_dir
    )
