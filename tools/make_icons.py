#!/usr/bin/env python3
"""Значки и маскоты для меню, студии и web-меню — из библиотеки картинок.

Источник — библиотека D:/Desktop/components/image (наклейки «Фиолетовая ночь»),
эмодзи нигде не используются. Скрипт берёт нужные файлы, уменьшает и пишет:
  assets/tm_ui/ic/<ключ>.png   значки внутриигрового меню (уезжают в game/tm_ui/)
  assets/tm_ui/m/<ключ>.png    маскоты пустых состояний меню
  assets/icons/<ключ>.png      значки и маскоты студии (PyQt6)
  engines/_shared/tm_icons.js  несколько значков data-URI для web-меню (Twine, RPG Maker)
PNG, а не webp: так значки читаются на любом Ren'Py (6.99+) и в любом Qt.

Запуск (нужен Pillow):  py -3.14 tools/make_icons.py
"""

import base64, io, os, sys

from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LIB = os.environ.get("TM_IMAGE_LIB", "D:/Desktop/components/image")
PAL = "Фиолетовая ночь"


def ic(group, name):
    return os.path.join(LIB, "04 Иконки", group, PAL, name + ".webp")


def masc(rel):
    return os.path.join(LIB, "03 Маскоты", rel)


# ключ -> исходник. Значки общие для меню и студии.
ICONS = {
    "rewind": ic("Время и конкурсы", "hourglass"),
    "stats": ic("RPG-лут", "red-health-potion"),
    "actions": ic("RPG-лут", "treasure-chest"),
    "scanner": ic("Интерфейс - основное", "magnifying-glass"),
    "story": ic("RPG-лут", "rolled-map-wax"),
    "settings": ic("Интерфейс - основное", "gear"),
    "logo": ic("Ретро-техника", "joystick"),
    "eye": ic("Интерфейс - действия", "eye"),
    "snow": os.path.join(LIB, "04 Иконки", "Погода", PAL, "snowflake.webp"),
    "close": ic("Интерфейс - знаки", "cross-circle"),
    "ok": ic("Интерфейс - знаки", "check-mark-circle"),
    "save": ic("Ретро-техника", "floppy-disk"),
    "load": ic("Интерфейс - основное", "folder"),
    "skip": ic("Интерфейс - знаки", "lightning-bolt"),
    "back": ic("Интерфейс - действия", "circular-sync-arrows"),
    "hint": ic("Реакции", "sparkles"),
    "warn": ic("Реакции", "exclamation-mark"),
    "camera": ic("Интерфейс - действия", "camera"),
    "console": ic("Интерфейс - действия", "terminal-window"),
    "pin": ic("Интерфейс - знаки", "pin"),
    "target": ic("Время и конкурсы", "target-arrow"),
    "trophy": ic("Время и конкурсы", "trophy-cup"),
    "palette": ic("Интерфейс - действия", "color-palette"),
    "key": ic("Интерфейс - основное", "key"),
    "bug": ic("Интерфейс - основное", "beetle-seen-above"),
    "coins": ic("RPG-лут", "stack-gold-coins"),
    "star": ic("Интерфейс - знаки", "star"),
    "plus": ic("Интерфейс - знаки", "plus-circle"),
    "trash": ic("Интерфейс - основное", "trash-bin"),
    "rocket": ic("Интерфейс - основное", "rocket"),
    "download": ic("Интерфейс - действия", "download-arrow"),
    "upload": ic("Интерфейс - действия", "upload-arrow"),
    "checklist": ic("Время и конкурсы", "checklist"),
    "house": ic("Интерфейс - знаки", "house"),
    "wrench": ic("Интерфейс - действия", "wrench"),
    "puzzle": ic("Интерфейс - действия", "puzzle-piece"),
    "clipboard": ic("Интерфейс - действия", "clipboard"),
    "brush": ic("Интерфейс - действия", "paint-brush"),
    "code": os.path.join(LIB, "04 Иконки", "Файлы", PAL, "code-file-brackets.webp"),
    "stopwatch": ic("Время и конкурсы", "stopwatch"),
    "flag": ic("Время и конкурсы", "finish-flag"),
    "question": ic("Интерфейс - знаки", "question-mark-bubble"),
    "remote": os.path.join(LIB, "04 Иконки", "Сеть", PAL, "satellite-dish.webp"),
    "play": os.path.join(LIB, "04 Иконки", "Медиа и плеер", PAL, "play-button.webp"),
}

MASCOTS = {
    "wait": masc("Новый стиль/mascot-waiting-patiently-holding.webp"),
    "search": masc("Из проектов/Поиск.webp"),
    "think": masc("Из проектов/Думает.webp"),
    "sad": masc("Новый стиль/mascot-sad-face-single.webp"),
    "party": masc("Лист 12 поз/pose-celebrating.webp"),
    "wave": masc("Новый стиль/mascot-waving-goodbye-one.webp"),
    "sleep": masc("Лист 12 поз/pose-sleeping-blanket.webp"),
    "wrench": masc("Лист 12 поз/pose-fixing-wrench.webp"),
}

# значки, которых в игре нет (только студия) — не тащим их в game/tm_ui
# (rocket, flag, checklist, code, download, upload — нужны вкладкам «Тест» и «Код»)
STUDIO_ONLY = {
    "plus",
    "trash",
    "house",
    "wrench",
    "puzzle",
    "clipboard",
    "brush",
    "stopwatch",
    "remote",
    "play",
}
# web-меню: значки для кнопок вместо ❄ / ✎ / 📷 (браузеры рисуют их цветными эмодзи)
WEB = ("snow", "edit", "camera", "swap")
WEB_SRC = {"snow": "snow", "edit": "brush", "camera": "camera", "swap": "back"}

ICON_PX = 64
MASCOT_PX = 220
WEB_PX = 40


def load(src, px):
    im = Image.open(src).convert("RGBA")
    box = im.getbbox()  # срезать прозрачные поля: значки одного кегля выглядят ровнее
    if box:
        im = im.crop(box)
    im.thumbnail((px, px), Image.LANCZOS)
    out = Image.new("RGBA", (px, px), (0, 0, 0, 0))
    out.paste(im, ((px - im.width) // 2, (px - im.height) // 2), im)
    return out


def small(im):
    """PNG-палитра на 256 цветов с альфой: втрое легче, на глаз не отличить."""
    return im.quantize(256, method=Image.Quantize.FASTOCTREE, dither=Image.Dither.NONE)


def save_png(im, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    small(im).save(path, optimize=True)


def main():
    missing = [
        k
        for k, p in list(ICONS.items()) + list(MASCOTS.items())
        if not os.path.exists(p)
    ]
    if missing:
        print("нет исходников в библиотеке:", ", ".join(missing))
        return 1
    game_ic = os.path.join(ROOT, "assets", "tm_ui", "ic")
    game_m = os.path.join(ROOT, "assets", "tm_ui", "m")
    studio = os.path.join(ROOT, "assets", "icons")
    for key, src in ICONS.items():
        im = load(src, ICON_PX)
        save_png(im, os.path.join(studio, key + ".png"))
        if key not in STUDIO_ONLY:
            save_png(im, os.path.join(game_ic, key + ".png"))
    for key, src in MASCOTS.items():
        im = load(src, MASCOT_PX)
        save_png(im, os.path.join(game_m, key + ".png"))
        save_png(im, os.path.join(studio, "m_" + key + ".png"))

    lines = [
        "// Сгенерировано tools/make_icons.py — значки web-меню (data-URI PNG), без эмодзи.",
        "var TM_ICONS = {",
    ]
    for key in WEB:
        buf = io.BytesIO()
        small(load(ICONS[WEB_SRC[key]], WEB_PX)).save(buf, "PNG", optimize=True)
        lines.append(
            '  %s: "data:image/png;base64,%s",'
            % (key, base64.b64encode(buf.getvalue()).decode())
        )
    lines.append("};")
    with open(
        os.path.join(ROOT, "engines", "_shared", "tm_icons.js"),
        "w",
        encoding="utf-8",
        newline="\n",
    ) as f:
        f.write("\n".join(lines) + "\n")

    total = 0
    for d in (game_ic, game_m, studio):
        total += sum(os.path.getsize(os.path.join(d, f)) for f in os.listdir(d))
    print(f"значков: {len(ICONS)}, маскотов: {len(MASCOTS)}, всего {total // 1024} КБ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
