#!/usr/bin/env python3
"""Статический скан Twine/SugarCube-истории — аналог tm.py curate для Ren'Py.

У Twine нет байткода: переменные истории — это `$name` в исходниках пассажей, а в
рантайме они лежат в `State.variables.name`. Скомпилированный `.html` держит пассажи
в `<tw-storydata>/<tw-passagedata>` (тело HTML-экранировано). Скан:
  * перечисляет имена `$var` (и `State.variables.x`) из пассажей,
  * по `<<set $x to VAL>>` / `<<set $x = VAL>>` подсказывает тип (num/bool/str).
Путь для меню — `State.variables.NAME`.

Использование:
    python scan.py <game.html|папка_с_html>
"""
import os, re, sys, glob, argparse
import html as htmllib

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "_shared")))
import tm_htmlio  # noqa: E402  (HTML не обязательно в UTF-8)

RE_STORY   = re.compile(r'<tw-storydata\b[^>]*>(.*?)</tw-storydata>', re.S | re.I)
RE_VAR     = re.compile(r'\$([A-Za-z_]\w*)')                 # $gold  (не $5 — только имена)
RE_STATE   = re.compile(r'State\.variables\.([A-Za-z_]\w*)')
RE_SET     = re.compile(r'<<set\s+\$([A-Za-z_]\w*)\s*(?:to\b|=)\s*([^>]+?)\s*>>', re.I)
RE_NUM     = re.compile(r'-?\d+(?:\.\d+)?$')
EXCLUDE    = {"args"}   # $args — аргументы макросов/виджетов, не переменные истории


def find_html(path):
    """Разрешить путь к .html: сам файл или папка (крупнейший *.html — история, не заглушка)."""
    if os.path.isfile(path) and path.lower().endswith(".html"):
        return path
    if os.path.isdir(path):
        htmls = glob.glob(os.path.join(glob.escape(path), "*.html"))
        if htmls:
            return max(htmls, key=os.path.getsize)
    raise FileNotFoundError(f"HTML Twine-игры не найден: {path}")


def _classify(expr):
    """Грубая классификация литерала присваивания: num / bool / str / '' (неизвестно)."""
    e = expr.strip()
    if RE_NUM.match(e):
        return "num"
    if e.lower() in ("true", "false"):
        return "bool"
    if len(e) >= 2 and e[0] == e[-1] and e[0] in ("'", '"'):
        return "str"
    return ""


def scan(path):
    """Кандидаты Twine: {html, variables=[(name, type_hint), ...]} (отсортировано по имени)."""
    html_path = find_html(path)
    raw = tm_htmlio.read(html_path)[0]
    m = RE_STORY.search(raw)
    region = htmllib.unescape(m.group(1) if m else raw)   # без tw-storydata — весь файл (fallback)

    types = {}
    for name, expr in RE_SET.findall(region):
        t = _classify(expr)
        if t:
            types.setdefault(name, t)
    names = (set(RE_VAR.findall(region)) | set(RE_STATE.findall(region))) - EXCLUDE
    return {"html": html_path,
            "variables": sorted((n, types.get(n, "")) for n in names)}


def report(path):
    """Человекочитаемый отчёт-кандидаты (как cand/game_N.txt для Ren'Py)."""
    c = scan(path)
    L = [f"# Twine scan: {c['html']}",
         f"# переменных: {len(c['variables'])}",
         "\n## ПЕРЕМЕННЫЕ (State.variables)  ->  ('Метка','State.variables.NAME')"]
    for name, t in c["variables"]:
        tag = f"   [{t}]" if t else ""
        L.append(f"${name}{tag}   ->   State.variables.{name}")
    return "\n".join(L) + "\n"


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("target", help="game.html или папка с ним")
    print(report(p.parse_args().target), end="")
