#!/usr/bin/env python3
"""Interactive setup for Kitty + VS Code + Pokemon-Terminal persistence."""

import json
import os
import re
import subprocess
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
POKEMON_BIN = REPO_ROOT / ".venv" / "bin" / "pokemon"
PYTHON_BIN = REPO_ROOT / ".venv" / "bin" / "python"
AUTOLOAD_SCRIPT = REPO_ROOT / "scripts" / "kitty_autoload.py"

CONFIG_DIR = Path.home() / ".config" / "pokemon-terminal"
STATE_FILE = CONFIG_DIR / "kitty-profile.json"
KITTY_CONF = Path.home() / ".config" / "kitty" / "kitty.conf"
ZSHRC = Path.home() / ".zshrc"
VSCODE_SETTINGS = Path.home() / "Library" / "Application Support" / "Code" / "User" / "settings.json"

KITTY_BLOCK_START = "# >>> pokemon-terminal kitty >>>"
KITTY_BLOCK_END = "# <<< pokemon-terminal kitty <<<"
ZSH_BLOCK_START = "# >>> pokemon-terminal kitty autoload >>>"
ZSH_BLOCK_END = "# <<< pokemon-terminal kitty autoload <<<"


def _read_json_file(path: Path):
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        return {}


def _strip_json_comments(text: str) -> str:
    def replacer(match: re.Match):
        token = match.group(0)
        if token.startswith("/"):
            return " "
        return token

    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE,
    )
    return re.sub(pattern, replacer, text)


def _strip_trailing_commas(text: str) -> str:
    output = []
    in_string = False
    string_quote = ""
    escape = False

    for i, char in enumerate(text):
        if in_string:
            output.append(char)
            if escape:
                escape = False
            elif char == "\\":
                escape = True
            elif char == string_quote:
                in_string = False
                string_quote = ""
            continue

        if char in {'"', "'"}:
            in_string = True
            string_quote = char
            output.append(char)
            continue

        if char == ",":
            j = i + 1
            while j < len(text) and text[j].isspace():
                j += 1
            if j < len(text) and text[j] in "]}":
                continue

        output.append(char)

    return "".join(output)


def _read_jsonc_file(path: Path):
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as handle:
            raw = handle.read().strip()
        if not raw:
            return {}
        normalized = _strip_trailing_commas(_strip_json_comments(raw))
        return json.loads(normalized)
    except OSError:
        return None
    except json.JSONDecodeError:
        return None


def _write_json_file(path: Path, payload: dict):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")


def _replace_or_append_block(path: Path, start: str, end: str, block_lines):
    content = ""
    if path.exists():
        with open(path, "r", encoding="utf-8") as handle:
            content = handle.read()
    block = "\n".join([start, *block_lines, end]) + "\n"
    if start in content and end in content:
        pattern = re.compile(re.escape(start) + r".*?" + re.escape(end) + r"\n?", re.DOTALL)
        content = pattern.sub(block, content)
    else:
        if content and not content.endswith("\n"):
            content += "\n"
        content += ("\n" if content else "") + block
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        handle.write(content)


def _configure_vscode_default_kitty():
    settings = _read_jsonc_file(VSCODE_SETTINGS)
    if settings is None:
        print(f"Skipping VS Code settings update (could not parse {VSCODE_SETTINGS}).")
        return False
    profiles_key = "terminal.integrated.profiles.osx"
    default_key = "terminal.integrated.defaultProfile.osx"
    profiles = settings.get(profiles_key)
    if not isinstance(profiles, dict):
        profiles = {}
    kitty_profile = profiles.get("kitty")
    if not isinstance(kitty_profile, dict):
        kitty_profile = {}
    kitty_profile.setdefault("path", "kitty")
    profiles["kitty"] = kitty_profile
    settings[profiles_key] = profiles
    settings[default_key] = "kitty"
    _write_json_file(VSCODE_SETTINGS, settings)
    return True


def _configure_kitty_remote_control(password: str):
    remote_line = f'remote_control_password "{password}" set-background-image set-colors'
    _replace_or_append_block(
        KITTY_CONF,
        KITTY_BLOCK_START,
        KITTY_BLOCK_END,
        [
            "allow_remote_control password",
            remote_line,
        ],
    )


def _install_zsh_autoload_hook():
    python_bin = str(PYTHON_BIN).replace('"', '\\"')
    autoload_script = str(AUTOLOAD_SCRIPT).replace('"', '\\"')
    block_lines = [
        "if [[ -n \"$KITTY_WINDOW_ID\" && -o interactive ]]; then",
        f"  if [[ -x \"{python_bin}\" && -f \"{autoload_script}\" ]]; then",
        f"    \"{python_bin}\" \"{autoload_script}\"",
        "  fi",
        "fi",
    ]
    _replace_or_append_block(ZSHRC, ZSH_BLOCK_START, ZSH_BLOCK_END, block_lines)


def _run_preview(selector: str, text_mode: str, password: str):
    if "KITTY_WINDOW_ID" not in os.environ:
        print("Not in a Kitty terminal, skipping live preview.")
        return

    env = os.environ.copy()
    env["POKEMON_TERMINAL_KITTY_TEXT_MODE"] = text_mode
    if password:
        env["KITTY_RC_PASSWORD"] = password

    cmd = [str(POKEMON_BIN)]
    selector = selector.strip()
    if selector:
        if selector.isdigit():
            cmd.append(selector)
        else:
            cmd.extend(["-n", selector.lower()])
    cmd.append("-v")
    subprocess.run(cmd, check=False, env=env)


def _save_state(selector: str, text_mode: str, password: str):
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "pokemon_selector": selector.strip(),
        "text_mode": text_mode,
        "kitty_rc_password": password,
        "pokemon_binary": str(POKEMON_BIN),
    }
    _write_json_file(STATE_FILE, payload)
    STATE_FILE.chmod(0o600)


def _prompt(prompt: str, default: str):
    value = input(f"{prompt} [{default}]: ").strip()
    return value if value else default


def _prompt_yes_no(prompt: str, default_yes=True):
    suffix = "Y/n" if default_yes else "y/N"
    value = input(f"{prompt} ({suffix}): ").strip().lower()
    if not value:
        return default_yes
    return value in {"y", "yes"}


def main():
    print("Pokemon-Terminal Kitty Setup Wizard")
    print("-----------------------------------")
    if not POKEMON_BIN.exists():
        print(f"Missing {POKEMON_BIN}. Run `make setup` first.")
        return 1

    existing = _read_json_file(STATE_FILE)
    selector = str(existing.get("pokemon_selector", "pikachu"))
    text_mode = str(existing.get("text_mode", "auto")).lower()
    if text_mode not in {"auto", "light", "dark"}:
        text_mode = "auto"
    password = str(existing.get("kitty_rc_password", "missingno"))

    if _prompt_yes_no("Set Kitty as default terminal profile in VS Code?", True):
        if _configure_vscode_default_kitty():
            print(f"Updated {VSCODE_SETTINGS}")

    if _prompt_yes_no("Configure Kitty remote control block in kitty.conf?", True):
        password = _prompt("Kitty remote-control password", password)
        _configure_kitty_remote_control(password)
        print(f"Updated {KITTY_CONF}")

    while True:
        print("")
        print(f"Current selector: {selector or '(random each start)'}")
        print(f"Current text mode: {text_mode}")
        print("Actions: [p] preview pokemon  [r] random preview  [m] text mode  [s] save+enable  [q] quit")
        choice = input("Choose action: ").strip().lower()

        if choice == "p":
            selector = input("Pokemon name or id: ").strip().lower()
            if selector:
                _run_preview(selector, text_mode, password)
        elif choice == "r":
            selector = ""
            _run_preview(selector, text_mode, password)
        elif choice == "m":
            mode = _prompt("Text mode (auto/light/dark)", text_mode).lower()
            if mode in {"auto", "light", "dark"}:
                text_mode = mode
                _run_preview(selector, text_mode, password)
            else:
                print("Invalid mode.")
        elif choice == "s":
            _save_state(selector, text_mode, password)
            _install_zsh_autoload_hook()
            print(f"Saved profile: {STATE_FILE}")
            print(f"Installed autoload hook in {ZSHRC}")
            print("Open a new Kitty tab/window to see the saved theme applied automatically.")
            return 0
        elif choice == "q":
            print("No changes saved.")
            return 0
        else:
            print("Invalid option.")


if __name__ == "__main__":
    raise SystemExit(main())
