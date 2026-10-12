#!/usr/bin/env python3
"""Статический скан игры Godot по .pck: переменные Dialogic и их условия в сценах (.dtl),
переменные глобальных объектов из GDScript (если скрипты лежат текстом, Godot 4.0–4.2).

Отчёт — подсказка для студии (вкладка «Кандидаты»): что есть в игре и что сценам нужно.
Значения правятся в игре меню (Shift+T), этот файл ничего не меняет.

    python scan.py <папка игры | .pck | .exe>
"""

import os
import re
import sys
from collections import defaultdict

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import pck as pckmod  # noqa: E402

CMP = re.compile(r"\{([\w.]+)\}\s*(>=|<=|==|!=|>|<)\s*(-?\d+(?:\.\d+)?)")
BARE = re.compile(r"(?:if|elif|\[if)\s+!?\{([\w.]+)\}")
SET = re.compile(r"set\s+\{([\w.]+)\}\s*(\+=|-=|=)\s*([^\n\]]+)")
GD_VAR = re.compile(r"^var\s+(\w+)\s*(?::\s*\w+)?\s*(?::?=)\s*(.+)$", re.M)


def scan(path):
    """{"version", "dialogic": {имя: {"chk": [(оп, число, сцена)], "set": [...] }}, "autoload": {...}}"""
    d = (
        os.path.dirname(path)
        if os.path.isfile(path) and not path.lower().endswith((".pck", ".exe"))
        else path
    )
    pack_path = path if os.path.isfile(path) else pckmod.find_pack(d)
    if not pack_path:
        raise FileNotFoundError(f"нет .pck Godot: {path}")
    p = pckmod.Pck(pack_path)
    dlg = defaultdict(lambda: {"chk": [], "set": []})
    for name in sorted(p.files):
        if not name.endswith(".dtl"):
            continue
        scene = os.path.splitext(os.path.basename(name))[0]
        try:
            text = p.text(name)
        except pckmod.PckError:
            continue
        for m in CMP.finditer(text):
            dlg[m.group(1)]["chk"].append((m.group(2), m.group(3), scene))
        for m in BARE.finditer(text):
            dlg[m.group(1)]["chk"].append(("", "", scene))
        for m in SET.finditer(text):
            dlg[m.group(1)]["set"].append(
                (m.group(2) + " " + m.group(3).strip()[:16], scene)
            )
    auto = {}
    for name in sorted(p.files):
        if name.startswith("res://addons/") or not name.endswith(".gd"):
            continue
        try:
            src = p.text(name)
        except pckmod.PckError:
            continue
        found = [(m.group(1), m.group(2).strip()[:30]) for m in GD_VAR.finditer(src)]
        if found:
            auto[name[6:]] = found
    return {
        "version": ".".join(map(str, p.version)),
        "dialogic": dict(dlg),
        "autoload": auto,
    }


def report(path):
    r = scan(path)
    out = [
        f"# Godot {r['version']}: {len(r['dialogic'])} переменных Dialogic в сценах, "
        f"{len(r['autoload'])} скриптов с переменными (текстом)",
        "",
    ]
    if r["dialogic"]:
        out.append(
            "## Переменные Dialogic (что проверяют сцены)  ->  правка в игре: Shift+T"
        )
        for name in sorted(r["dialogic"], key=lambda n: -len(r["dialogic"][n]["chk"])):
            u = r["dialogic"][name]
            need = sorted({f"{op} {num}" for op, num, _s in u["chk"] if op})
            scenes = sorted({s for _o, _n, s in u["chk"]})
            line = f"{name} -> {name}"
            if need:
                line += "   нужно: " + ", ".join(need[:6])
            if scenes:
                line += f"   сцены: {', '.join(scenes[:4])}" + (
                    f" и ещё {len(scenes) - 4}" if len(scenes) > 4 else ""
                )
            if u["set"]:
                line += f"   меняется: {u['set'][0][0]} ({u['set'][0][1]})"
            out.append(line)
        out.append("")
    if r["autoload"]:
        out.append("## Переменные скриптов (GDScript текстом)")
        for f, vs in r["autoload"].items():
            out.append(f"# {f}")
            for n, v in vs:
                out.append(f"{n} = {v}")
        out.append("")
    if not r["dialogic"] and not r["autoload"]:
        out.append(
            "Сцен Dialogic и текстовых скриптов нет (скрипты скомпилированы). Меню в игре всё равно "
            "находит переменные само: Shift+T -> «Переменные» / «Поиск»."
        )
    return "\n".join(out)


if __name__ == "__main__":
    print(report(sys.argv[1]))
