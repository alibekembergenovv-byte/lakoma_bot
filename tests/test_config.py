import os
import pytest
from pathlib import Path
from bot.config import load_config
from bot.database.seed_data import INITIAL_REGIONS_AND_HOSPITALS

def test_load_config_defaults(tmp_path, monkeypatch):
    monkeypatch.setenv("BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    monkeypatch.setenv("ADMIN_IDS", "12345678,87654321")
    
    cfg = load_config()
    assert cfg.bot_token == "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11"
    assert cfg.admin_ids == [12345678, 87654321]
    assert isinstance(cfg.db_path, Path)
    assert isinstance(cfg.exports_dir, Path)

def test_seed_data_integrity():
    assert "Qaraózek" in INITIAL_REGIONS_AND_HOSPITALS
    assert "Taxtakópir" in INITIAL_REGIONS_AND_HOSPITALS
    assert "Shımbay" in INITIAL_REGIONS_AND_HOSPITALS
    assert len(INITIAL_REGIONS_AND_HOSPITALS["Qaraózek"]) > 0
    all_facilities = [h for hosp_list in INITIAL_REGIONS_AND_HOSPITALS.values() for h in hosp_list]
    assert len(all_facilities) == 8
