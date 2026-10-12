#!/usr/bin/env python3
"""Ядро tm.py gen: рендер per-game zzz_testmenu_data.rpy из манифеста.

Данные (заголовок, акцент, статы, действия) живут в манифесте — здесь только рендер.
Пишет в build/game_{i}/zzz_testmenu_data.rpy.
"""

import os

from tmkit.games import GAMES, ACCENT
from tmkit.paths import BUILD, TWEAKS_DIR
from tmkit import report
from tmkit.validate import accent_hex

OUT = BUILD

HEADER = """# =====================================================================
#  TEST MENU — data (game_{i})   [автогенерация из манифеста]
#  Заголовок, акцент, список статов и действий. Открытие меню: Shift+T.
#  Работает в паре с zzz_testmenu_engine.rpy
# =====================================================================
init -20 python:
    store.tm_title = "{title}"
    store.tm_accent = "{accent}"
    store.tm_stats = [
{rows}
    ]
    store.tm_actions = [
{actions}
    ]
"""


def esc(s):
    """Экранировать строку для литерала в двойных кавычках. Перевод строки/табуляция
    из вставленного в таблицу текста иначе рвут литерал и ломают .rpy."""
    return (
        s.replace("\\", "\\\\")
        .replace('"', '\\"')
        .replace("\r", "\\r")
        .replace("\n", "\\n")
        .replace("\t", "\\t")
    )


def rows_of(pairs):
    # ("Метка", "путь") или ("Метка", "путь", "min", "max") — см. manifest.trim_row
    from tmkit.manifest import trim_row

    return "\n".join(
        "        (%s)," % ", ".join('"%s"' % esc(x) for x in trim_row(row)) for row in pairs
    )


def data_path(i):
    return os.path.join(OUT, f"game_{i}", "zzz_testmenu_data.rpy")


def tweak_path(name):
    """Файл твика по имени из манифеста (только имя в tweaks/, без подпапок)."""
    return os.path.join(TWEAKS_DIR, os.path.basename(name or ""))


def tweak_text(name):
    """Текст твика или None (нет поля / нет файла)."""
    if not name:
        return None
    try:
        with open(tweak_path(name), encoding="utf-8", newline="") as f:
            return f.read().replace("\r\n", "\n")
    except OSError:
        return None


def render_game(i, g, default_accent=ACCENT):
    """Текст data-файла для записи манифеста g (без записи на диск). Отдельно от
    render(i): студия рендерит свою копию манифеста, а не снимок GAMES на импорт."""
    # per-game акцент; пусто/не hex = глобальный дефолт (Ren'Py падает на «red» и т.п.)
    accent = accent_hex(g.get("accent")) or accent_hex(default_accent) or "#38e0c8"
    text = HEADER.format(
        i=i,
        title=esc(g.get("title") or "TEST MENU"),
        accent=accent,
        rows=rows_of(g.get("stats", [])),
        actions=rows_of(g.get("actions", [])),
    )
    tw = tweak_text(g.get("tweak"))
    if tw:
        text += (
            "\n# =====================================================================\n"
            "#  Твик игры: tweaks/%s (снимается вместе с меню)\n"
            "# =====================================================================\n" % os.path.basename(g["tweak"])
        ) + tw.rstrip("\n") + "\n"
    return text


def render(i):
    """Текст data-файла игры game_{i} по текущему манифесту."""
    return render_game(i, GAMES[i])


def is_stale(i):
    """Нет data-файла в build/ или он разошёлся с манифестом."""
    try:
        with open(data_path(i), encoding="utf-8", newline="") as f:
            return f.read() != render(i)
    except OSError:
        return True


def gen(i):
    g = GAMES[i]
    stats = g.get("stats", [])
    acts = g.get("actions", [])
    if g.get("accent") and not accent_hex(g["accent"]):
        report.note(i, f"акцент «{g['accent']}» не #rrggbb — взят глобальный")
    if g.get("tweak") and tweak_text(g["tweak"]) is None:
        report.warn(i, f"твик «{g['tweak']}» не найден в tweaks/ — data без твика")
    path = data_path(i)
    d = os.path.dirname(path)
    os.makedirs(d, exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(render(i))
    n_stats = len([s for s in stats if s[1]])  # непустой путь = реальный стат
    n_sec_s = len([s for s in stats if not s[1]])  # заголовки секций
    n_acts = len([a for a in acts if a[1]])
    n_sec_a = len([a for a in acts if not a[1]])
    report.info(
        i,
        f"{n_stats} статов (+{n_sec_s} секц.), "
        f"{n_acts} действий (+{n_sec_a} секц.) -> {d}",
    )
