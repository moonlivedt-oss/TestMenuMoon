#!/usr/bin/env python3
"""Статический скан данных RPG Maker MV/MZ — аналог curate_dump для Ren'Py.

Эвристики не нужны: RPG Maker хранит человекочитаемые имена прямо в data/*.json:
  * System.json  -> variables[] и switches[] (имя по индексу),
  * Items/Weapons/Armors.json -> id + name (для «выдать предмет»),
  * System.json.currencyUnit  -> подпись валюты (деньги через $gameParty.gainGold).
Пути в игре: $gameVariables.value(N), $gameSwitches.value(N), $gameParty.gainItem(...).

Использование:
    python scan.py <папка_игры|data|www/data>
"""
import os, json, argparse

DATA_SUBPATHS = (("data",), ("www", "data"), ("package.nw", "data"), ("package.nw", "www", "data"))
ITEM_KINDS = (("ПРЕДМЕТЫ", "items", "Items.json", "$dataItems"),
              ("ОРУЖИЕ", "weapons", "Weapons.json", "$dataWeapons"),
              ("БРОНЯ", "armors", "Armors.json", "$dataArmors"))


def find_data_dir(path):
    """Разрешить папку data/: сама папка data, папка_игры/data или папка_игры/www/data."""
    if (os.path.isdir(path)
            and os.path.basename(path.rstrip("/\\")).lower() == "data"
            and os.path.exists(os.path.join(path, "System.json"))):
        return path
    for parts in DATA_SUBPATHS:
        cand = os.path.join(path, *parts)
        if os.path.exists(os.path.join(cand, "System.json")):
            return cand
    raise FileNotFoundError(f"data/System.json не найден в {path}")


def _load(data_dir, name):
    p = os.path.join(data_dir, name)
    if not os.path.exists(p):
        return None
    with open(p, encoding="utf-8-sig") as f:   # RPG Maker JSON бывает с BOM
        return json.load(f)


def _named(arr):
    """[(index, name)] для непустых имён; индекс 0 в RPG Maker всегда пустой/null."""
    out = []
    for idx, name in enumerate(arr or []):
        if isinstance(name, str) and name.strip():
            out.append((idx, name.strip()))
    return out


def _named_records(arr):
    """[(id, name)] для записей data-массива (Items/Weapons/Armors); нулевой элемент null."""
    out = []
    for rec in arr or []:
        if isinstance(rec, dict) and isinstance(rec.get("name"), str) and rec["name"].strip():
            out.append((rec.get("id"), rec["name"].strip()))
    return out


def scan(path):
    """Структурированные кандидаты: variables/switches/items/weapons/armors/currency."""
    data_dir = find_data_dir(path)
    system = _load(data_dir, "System.json") or {}
    out = {
        "data_dir": data_dir,
        "variables": _named(system.get("variables")),
        "switches": _named(system.get("switches")),
        "currency": (system.get("currencyUnit") or "").strip(),
    }
    for _title, key, fname, _arr in ITEM_KINDS:
        out[key] = _named_records(_load(data_dir, fname))
    return out


def report(path):
    """Человекочитаемый отчёт-кандидаты (как cand/game_N.txt для Ren'Py)."""
    c = scan(path)
    L = [f"# RPG Maker scan: {c['data_dir']}",
         f"# именованных переменных: {len(c['variables'])}, переключателей: {len(c['switches'])}, "
         f"предметов: {len(c['items'])}, оружия: {len(c['weapons'])}, брони: {len(c['armors'])}"]

    L.append(f"\n## ДЕНЬГИ  ->  для tm_actions (валюта: {c['currency'] or '?'})")
    L.append("$gameParty.gainGold(1000)")

    L.append("\n## ПЕРЕМЕННЫЕ (именованные)  ->  ('Метка','$gameVariables.value(N)')")
    for idx, name in c["variables"]:
        L.append(f"var {idx} = {name!r}   ->   $gameVariables.value({idx})")

    L.append("\n## ПЕРЕКЛЮЧАТЕЛИ (именованные)  ->  ('Метка','$gameSwitches.value(N)')")
    for idx, name in c["switches"]:
        L.append(f"switch {idx} = {name!r}   ->   $gameSwitches.value({idx})")

    for title, key, _fname, arr in ITEM_KINDS:
        L.append(f"\n## {title}  ->  для «выдать предмет» ($gameParty.gainItem)")
        for iid, name in c[key]:
            L.append(f"id {iid} = {name!r}   ->   $gameParty.gainItem({arr}[{iid}], 1)")

    return "\n".join(L) + "\n"


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("target", help="папка игры, data/ или www/data")
    print(report(p.parse_args().target), end="")
