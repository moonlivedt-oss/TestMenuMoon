#!/usr/bin/env python3
"""Офлайн-проверка данных манифеста (без запуска Ren'Py).

Ловит частые ошибки в stats/actions ДО деплоя:
  * код действия не компилируется (синтаксис) — через compile(), БЕЗ исполнения;
  * путь стата не разбирается как выражение, либо в него нельзя записать
    (кончается вызовом/литералом — меню покажет значение, но −/+/ввод не сработают);
  * дубли путей статов / кодов действий;
  * непустой путь/код без метки;
  * акцент не в виде #rgb / #rrggbb (Ren'Py упадёт на старте на «red» и т.п.).

Пути статов резолвятся на store игры, поэтому «правильность» пути проверить офлайн
нельзя — это делает движок (кнопка «Проверить всё») уже в запущенной игре.
Здесь — только то, что проверяемо без игрового процесса.
"""

import ast, re

_RE_HEX = re.compile(r"^#([0-9a-fA-F]{3}|[0-9a-fA-F]{6})$")


def accent_hex(s):
    """Нормализовать акцент к '#rrggbb' (нижний регистр) или None, если это не hex-цвет.
    Движок и JS-ядро клеят к акценту альфа-суффикс, поэтому нужен ровно #rrggbb."""
    m = _RE_HEX.match((s or "").strip())
    if not m:
        return None
    h = m.group(1).lower()
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return "#" + h


def _real_rows(pairs):
    """(индекс, метка, значение) для строк с НЕпустым значением — заголовки секций
    (значение пустое) пропускаем."""
    for idx, row in enumerate(pairs):
        label, value = row[0], row[1]
        if value:
            yield idx, label, value


def _path_problem(path):
    """Текст проблемы пути стата или None. Путь должен быть выражением, в которое
    можно записать: имя, атрибут или элемент по индексу/ключу."""
    try:
        node = ast.parse(path.strip(), mode="eval").body
    except SyntaxError as e:
        return f"путь не разбирается — {e.msg}"
    if not isinstance(node, (ast.Name, ast.Attribute, ast.Subscript)):
        return "только чтение (путь кончается не именем/атрибутом/[ключом])"
    return None


def _num(s):
    try:
        return float(str(s).replace(",", "."))
    except ValueError:
        return None


def check_limits(stats):
    """Границы min/max: число или выражение игры; min <= max, если оба числа."""
    issues = []
    for idx, row in enumerate(stats):
        if len(row) < 3:
            continue
        label = row[0] or "#%d" % (idx + 1)
        mn, mx = (tuple(row[2:4]) + ("", ""))[:2]
        if (mn or mx) and not row[1]:
            issues.append(f"секция «{label}»: границы у заголовка секции ни на что не влияют")
        for name, spec in (("min", mn), ("max", mx)):
            if spec and _num(spec) is None:
                try:
                    ast.parse(str(spec).strip(), mode="eval")
                except SyntaxError as e:
                    issues.append(f"стат «{label}»: {name} «{spec}» не разбирается — {e.msg}")
        a = _num(mn) if mn else None
        b = _num(mx) if mx else None
        if a is not None and b is not None and a > b:
            issues.append(f"стат «{label}»: min {mn} больше max {mx}")
    return issues


def check_stats(stats):
    issues = check_limits(stats)
    seen = {}
    for idx, label, path in _real_rows(stats):
        if not label.strip():
            issues.append(f"стат #{idx + 1}: путь «{path}» без метки")
        problem = _path_problem(path)
        if problem:
            issues.append(f"стат «{label or '#%d' % (idx + 1)}»: {problem}")
        if path in seen:
            issues.append(f"стат «{label}»: путь-дубль «{path}» (уже у «{seen[path]}»)")
        else:
            seen[path] = label
    return issues


def check_actions(actions):
    issues = []
    seen = {}
    for idx, label, code in _real_rows(actions):
        if not label.strip():
            issues.append(f"действие #{idx + 1}: код без метки")
        try:
            compile(code, "<action>", "exec")  # только компиляция, не исполнение
        except SyntaxError as e:
            issues.append(
                f"действие «{label or '#%d' % (idx + 1)}»: синтаксис — {e.msg}"
            )
        if code in seen:
            issues.append(f"действие «{label}»: код-дубль (уже у «{seen[code]}»)")
        else:
            seen[code] = label
    return issues


def check_accent(accent):
    """Пустой акцент = наследовать глобальный — это не проблема."""
    if accent and accent_hex(accent) is None:
        return [f"акцент «{accent}»: нужен #rgb или #rrggbb (будет взят глобальный)"]
    return []


def check_tweak(tweak):
    """Твик игры: файл должен лежать в tweaks/."""
    if not tweak:
        return []
    from tmkit.generate import tweak_text

    if tweak_text(tweak) is None:
        return [f"твик «{tweak}»: нет файла в tweaks/"]
    return []


def check_game(stats, actions, accent=None, tweak=None):
    """Полный список проблем (строки) для одной игры. Пусто = всё чисто."""
    return check_stats(stats) + check_actions(actions) + check_accent(accent) + check_tweak(tweak)
