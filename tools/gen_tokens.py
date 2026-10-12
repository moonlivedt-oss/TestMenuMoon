#!/usr/bin/env python3
"""Собрать набор цветов и размеров из engines/_shared/tm_tokens.json для всех оболочек.

    python tools/gen_tokens.py           пересобрать файлы
    python tools/gen_tokens.py --check   только проверить, что файлы свежие (код выхода 1 — нет)

Выход (правится JSON, эти файлы — пересобираются; тест сверяет, что они свежие):
    engines/renpy/engine/00_tokens.rpy   меню Ren'Py: TM_TOK, TM_TOK_ENGINE
    engines/_shared/tm_tokens.js         веб-меню (Twine, HTML5, RPG Maker): TM_TOK
    tmstudio/tokens.py                   студия: TOK, ENGINE, SIZE, RADIUS, SPACE, MOTION
    блок TM_TOKENS_START … TM_TOKENS_END в меню Godot 4/3, Unity (IL2CPP и Mono), GameMaker
"""

import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "engines", "_shared", "tm_tokens.json")
OUT_RPY = os.path.join(ROOT, "engines", "renpy", "engine", "00_tokens.rpy")
OUT_JS = os.path.join(ROOT, "engines", "_shared", "tm_tokens.js")
OUT_PY = os.path.join(ROOT, "tmstudio", "tokens.py")

NOTE = "Собран tools/gen_tokens.py из engines/_shared/tm_tokens.json — правь JSON, не этот файл."


def load():
    with open(SRC, encoding="utf-8") as f:
        return json.load(f)


def _q(s):
    return json.dumps(s, ensure_ascii=False)


def _dict_lines(d, indent):
    pad = " " * indent
    return "".join(f"{pad}{_q(k)}: {_q(v)},\n" for k, v in d.items())


def _engines(t):
    """Плашка движка: имя, цвет текста, фон (тот же цвет с прозрачностью)."""
    return {k: [name, col, col + "2e"] for k, (name, col) in t["engine"].items()}


def gen_rpy(t):
    eng = "".join(f"        {_q(k)}: ({_q(n)}, {_q(c)}, {_q(b)}),\n" for k, (n, c, b) in _engines(t).items())
    return (
        "# ==================== единый набор цветов и размеров ====================\n"
        f"# {NOTE}\n"
        '# Цвета с прозрачностью: TM_TOK["bg_panel"] + "f7".\n'
        "init -100 python:\n"
        "    TM_TOK = {\n" + _dict_lines(t["color"], 8) + "    }\n"
        "    # движок: (имя, цвет текста, фон плашки)\n"
        "    TM_TOK_ENGINE = {\n" + eng + "    }\n"
    )


def gen_js(t):
    body = dict(t["color"])
    lines = _dict_lines(body, 2)
    eng = "".join(f"  {_q(k)}: [{_q(n)}, {_q(c)}, {_q(b)}],\n" for k, (n, c, b) in _engines(t).items())
    nums = {
        **{"size_" + k: v for k, v in t["size"].items()},
        **{"radius_" + k: v for k, v in t["radius"].items()},
        **{"motion_" + k: v for k, v in t["motion"].items()},
    }
    return (
        f"/* {NOTE}\n"
        ' * Цвета с прозрачностью: K.bg_panel + "f7". */\n'
        "var TM_TOK = {\n"
        + lines
        + "".join(f"  {_q(k)}: {v},\n" for k, v in nums.items())
        + "  engine: {\n"
        + "".join("  " + ln + "\n" for ln in eng.rstrip("\n").split("\n"))
        + "  }\n};\n"
    )


def gen_py(t):
    eng = "".join(f"    {_q(k)}: ({_q(n)}, {_q(c)}, {_q(b)}),\n" for k, (n, c, b) in _engines(t).items())
    return (
        f'"""Набор цветов и размеров студии. {NOTE}"""\n\n'
        "TOK = {\n" + _dict_lines(t["color"], 4) + "}\n\n"
        "# движок: (имя, цвет текста, фон плашки)\n"
        "ENGINE = {\n" + eng + "}\n\n"
        "SIZE = {\n" + _dict_lines(t["size"], 4) + "}\n"
        "RADIUS = {\n" + _dict_lines(t["radius"], 4) + "}\n"
        f"SPACE = {t['space']!r}\n"
        "MOTION = {\n" + _dict_lines(t["motion"], 4) + "}\n"
    )


# Меню на других языках: блок между строками-маркерами TM_TOKENS_START / TM_TOKENS_END
# переписывается прямо в исходнике. (путь, вид, отступ, [(имя в коде, цвет из набора)])
ENG = os.path.join(ROOT, "engines")
TARGETS = [
    (
        os.path.join(ENG, "godot", "tm_menu.gd"),
        "gd",
        "",
        [
            ("ACCENT", "accent"),
            ("BG", "bg_panel"),
            ("BG2", "bg_card"),
            ("BG3", "bg_control"),
            ("TXT", "text"),
            ("DIM", "text_hint"),
            ("BAD", "err"),
            ("GOOD", "ok"),
            ("WARN", "warn"),
            ("INK", "on_accent"),
            ("LINE", "line"),
        ],
    ),
    (
        os.path.join(ENG, "godot", "tm_menu3.gd"),
        "gd",
        "",
        [
            ("ACCENT", "accent"),
            ("BG", "bg_panel"),
            ("BG2", "bg_control"),
            ("TXT", "text"),
            ("DIM", "text_hint"),
            ("WARN", "warn"),
            ("INK", "on_accent"),
        ],
    ),
    (
        os.path.join(ENG, "unity", "plugin", "Plugin.cs"),
        "cs",
        " " * 8,
        [
            ("Bg", "bg_panel"),
            ("Bg2", "bg_card"),
            ("Bg3", "bg_control"),
            ("Acc", "accent"),
            ("Txt", "text"),
            ("Dim", "text_hint"),
            ("Ink", "on_accent"),
            ("Err", "err"),
            ("Line", "line"),
        ],
    ),
    (
        os.path.join(ENG, "unity", "mono", "TestMenuMono.cs"),
        "cs",
        " " * 8,
        [("Bg", "bg_panel"), ("Acc", "accent"), ("Txt", "text"), ("Dim", "text_hint")],
    ),
    (
        os.path.join(ENG, "gamemaker", "menu_draw.gml"),
        "gml",
        "",
        [("_acc", "accent"), ("_txt", "text"), ("_dim", "text_hint"), ("_warn", "warn"), ("_frozen", "frozen")],
    ),
]
MARK_START, MARK_END = "TM_TOKENS_START", "TM_TOKENS_END"


def _rgb(h):
    return tuple(int(h[i : i + 2], 16) for i in (1, 3, 5))


def _target_line(kind, name, h):
    r, g, b = _rgb(h)
    if kind == "gd":
        return f'const {name} = Color("{h[:7]}")'
    if kind == "cs":
        return f"static readonly Color {name} = new Color({r / 255:.3f}f, {g / 255:.3f}f, {b / 255:.3f}f, 1f);"
    return f"var {name} = make_color_rgb({r}, {g}, {b});"


def splice(text, kind, indent, names, colors):
    """Текст исходника с пересобранным блоком цветов (без маркеров — ValueError)."""
    lines = text.replace("\r\n", "\n").split("\n")
    try:
        a = next(i for i, ln in enumerate(lines) if MARK_START in ln)
        z = next(i for i, ln in enumerate(lines) if MARK_END in ln)
    except StopIteration:
        raise ValueError("нет маркеров " + MARK_START) from None
    c = "#" if kind == "gd" else "//"
    block = [f"{indent}{c} {MARK_START}: цвета из engines/_shared/tm_tokens.json (python tools/gen_tokens.py)"]
    block += [indent + _target_line(kind, n, colors[k]) for n, k in names]
    block.append(f"{indent}{c} {MARK_END}")
    return "\n".join(lines[:a] + block + lines[z + 1 :])


def outputs():
    t = load()
    out = [(OUT_RPY, gen_rpy(t)), (OUT_JS, gen_js(t)), (OUT_PY, gen_py(t))]
    for path, kind, indent, names in TARGETS:
        out.append((path, splice(_read(path) or "", kind, indent, names, t["color"])))
    return out


def _read(path):
    try:
        with open(path, encoding="utf-8", newline="") as f:
            return f.read().replace("\r\n", "\n")
    except OSError:
        return None


def stale():
    """Файлы, которые не совпадают с JSON."""
    return [p for p, text in outputs() if _read(p) != text]


def main(argv):
    if "--check" in argv:
        bad = stale()
        for p in bad:
            print("устарел:", os.path.relpath(p, ROOT))
        return 1 if bad else 0
    for path, text in outputs():
        # перевод строк — как у файла сейчас (исходники движков бывают и с LF)
        try:
            crlf = b"\r\n" in open(path, "rb").read()
        except OSError:
            crlf = True
        with open(path, "w", encoding="utf-8", newline="\r\n" if crlf else "\n") as f:
            f.write(text)
        print("собран:", os.path.relpath(path, ROOT))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
