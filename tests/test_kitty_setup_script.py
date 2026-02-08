import importlib.util
from pathlib import Path


SCRIPT_PATH = Path(__file__).resolve().parents[1] / "scripts" / "kitty_setup.py"
SPEC = importlib.util.spec_from_file_location("kitty_setup", SCRIPT_PATH)
kitty_setup = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(kitty_setup)


def test_read_jsonc_valid(tmp_path):
    file_path = tmp_path / "settings.json"
    file_path.write_text('{"a": 1}', encoding="utf-8")
    assert kitty_setup._read_jsonc_file(file_path) == {"a": 1}


def test_read_jsonc_invalid_returns_none(tmp_path):
    file_path = tmp_path / "settings.json"
    file_path.write_text('{"a": 1,}', encoding="utf-8")
    assert kitty_setup._read_jsonc_file(file_path) is None
