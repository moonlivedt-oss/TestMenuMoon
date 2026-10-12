"""Набор цветов и размеров студии. Собран tools/gen_tokens.py из engines/_shared/tm_tokens.json — правь JSON, не этот файл."""

TOK = {
    "bg_window": "#0b0e14",
    "bg_panel": "#10141d",
    "bg_card": "#161b26",
    "bg_control": "#1e2432",
    "bg_popup": "#242c3a",
    "bg_deep": "#080b11",
    "shade": "#05070b",
    "line_soft": "#242c3a",
    "line": "#313a4c",
    "text_bright": "#ffffff",
    "text": "#e7ebf2",
    "text_dim": "#c7ccd4",
    "text_hint": "#9aa3b4",
    "text_off": "#5b6373",
    "accent": "#38e0c8",
    "on_accent": "#07110f",
    "on_accent_light": "#e7fffb",
    "ok": "#5ad469",
    "warn": "#ffb454",
    "err": "#ff6b6b",
    "info": "#6cb6ff",
    "frozen": "#9fd8ff",
    "call": "#d6b8ff",
    "tint_1": "#ffffff0a",
    "tint_2": "#ffffff12",
    "tint_3": "#ffffff1e",
    "tint_4": "#ffffff3a",
}

# движок: (имя, цвет текста, фон плашки)
ENGINE = {
    "renpy": ("Ren'Py", "#c4b5fd", "#c4b5fd2e"),
    "rpgmaker": ("RPG Maker", "#7ef0dd", "#7ef0dd2e"),
    "unity": ("Unity", "#fdba74", "#fdba742e"),
    "godot": ("Godot", "#93c5fd", "#93c5fd2e"),
    "unreal": ("Unreal", "#fca5a5", "#fca5a52e"),
    "gamemaker": ("GameMaker", "#86efac", "#86efac2e"),
    "twine": ("Twine", "#f9a8d4", "#f9a8d42e"),
    "construct": ("Construct", "#fde68a", "#fde68a2e"),
    "web": ("HTML5", "#c7ccd4", "#c7ccd42e"),
}

SIZE = {
    "title": 18,
    "h": 15,
    "body": 13,
    "small": 11,
}
RADIUS = {
    "chip": 6,
    "btn": 8,
    "card": 12,
}
SPACE = [4, 8, 12, 16, 24]
MOTION = {
    "fast": 120,
    "base": 180,
}
