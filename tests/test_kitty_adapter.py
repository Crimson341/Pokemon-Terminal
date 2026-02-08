from pokemonterminal.terminal.adapters import kitty
from pokemonterminal.terminal.adapters.kitty import KittyProvider


def test_kitty_compatible(monkeypatch):
    monkeypatch.setenv("KITTY_WINDOW_ID", "12")
    assert KittyProvider.is_compatible()
    monkeypatch.delenv("KITTY_WINDOW_ID")
    assert not KittyProvider.is_compatible()


def test_kitty_change_terminal_applies_background_and_colors(monkeypatch):
    calls = []

    def fake_run(args, check, capture_output):
        calls.append(args)

    monkeypatch.setattr(kitty, "run", fake_run)
    monkeypatch.setattr(kitty, "_infer_dark_threshold", lambda _: 0.9)
    monkeypatch.setattr(kitty, "_convert_to_png", lambda p: "/tmp/025.png")

    KittyProvider.change_terminal("/tmp/025.jpg")

    assert calls[0][:3] == ["kitty", "@", "set-background-image"]
    assert calls[0][3] == "/tmp/025.png"
    assert calls[1][:3] == ["kitty", "@", "set-colors"]
    assert any(arg.startswith("foreground=") for arg in calls[1][3:])


def test_kitty_text_mode_overrides(monkeypatch):
    monkeypatch.setattr(kitty, "_infer_dark_threshold", lambda _: 0.1)

    monkeypatch.setenv("POKEMON_TERMINAL_KITTY_TEXT_MODE", "dark")
    assert kitty._palette_for_path("/tmp/025.jpg") == kitty.LIGHT_BG_PALETTE

    monkeypatch.setenv("POKEMON_TERMINAL_KITTY_TEXT_MODE", "light")
    assert kitty._palette_for_path("/tmp/025.jpg") == kitty.DARK_BG_PALETTE

    monkeypatch.setenv("POKEMON_TERMINAL_KITTY_TEXT_MODE", "auto")
    assert kitty._palette_for_path("/tmp/025.jpg") == kitty.DARK_BG_PALETTE


def test_kitty_clear_resets_background_and_colors(monkeypatch):
    calls = []

    def fake_run(args, check, capture_output):
        calls.append(args)

    monkeypatch.setattr(kitty, "run", fake_run)
    KittyProvider.clear()

    assert calls[0] == ["kitty", "@", "set-background-image", "none"]
    assert calls[1] == ["kitty", "@", "set-colors", "--reset"]


def test_kitty_convert_png_passthrough(tmp_path):
    png = tmp_path / "x.png"
    png.write_bytes(b"\x89PNG\r\n\x1a\n")
    assert kitty._convert_to_png(str(png)) == str(png)
