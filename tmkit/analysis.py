#!/usr/bin/env python3
"""Ядро curate_dump: поиск кандидатов статов/инвентаря в распакованных исходниках.

Ищет НЕ только плоские `default/define NAME = число`, но и то, что раньше
приходилось копать вручную:
  * плоские присваивания — `default/define`, `$ NAME = N`, а также присваивания на
    базовом уровне `python:` / `init python:` блоков (локалы в теле def не берутся),
  * объектные статы  — классы с числовыми полями: `self.attr = N` и поля тела класса
    `attr = N` (+ где создан инстанс),
  * dict-статы       — `default NAME = { ... : N ... }` (одно- и многострочные, с учётом
    вложенности), напр. player_data,
  * инвентарные API  — add_item / class Inventory / take / деньги-сеттер.
Метки статов отбираются по ключевым словам с матчингом по границе токена (не подстрокой).
Секции помечены, чтобы по ним быстро собрать tm_stats / tm_actions.
Пишет отчёт в cand/game_X.txt.
"""

import os, re, glob, collections

from tmkit.paths import ANA_BASE, CAND_DIR, ana_dir, cand_file
from tmkit import report

# --- плоские глобалы: default/define NAME = число|bool  (NAME может быть obj.attr) ---
RE_FLAT = re.compile(
    r"^\s*(?:default|define)\s+([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*(-?\d+(?:\.\d+)?|True|False)\s*(?:#.*)?$"
)
# --- $-строка Ren'Py: `$ NAME = число|bool` (A1) ---
RE_DOLLAR = re.compile(
    r"^\s*\$\s*([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*(-?\d+(?:\.\d+)?|True|False)\s*(?:#.*)?$"
)
# --- заголовок python-блока: `python:` / `init [offset] python:` (A1) ---
RE_PYHEAD = re.compile(r"^(\s*)(?:init\s+(?:[-+]?\d+\s+)?)?python\b[^:]*:\s*$")
# --- присваивание внутри python-блока: `NAME = число|bool` (A1) ---
RE_PYASSIGN = re.compile(
    r"^(\s*)([A-Za-z_][A-Za-z0-9_.]*)\s*=\s*(-?\d+(?:\.\d+)?|True|False)\s*(?:#.*)?$"
)

# --- инвентарные / предметные API ---
RE_INV = re.compile(
    r"\b(?:def\s+(?:add_item|add_to_inventory|give_item|gain_item|obtain|acquire|pickup)\b"
    r"|def\s+take\s*\(|def\s+add\s*\(\s*self\s*,\s*item"
    r"|class\s+\w*Inventor\w*)"
)
# --- деньги ---
RE_MONEY = re.compile(
    r"(?:@\w*[Mm]oney\w*\.setter|def\s+money\b|\b_money\b|def\s+(?:gain_money|spend_money|add_money)\b)"
)

# --- объектные статы ---
RE_CLASS = re.compile(r"^(\s*)class\s+([A-Za-z_]\w*)")
RE_SELFNUM = re.compile(r"^\s*self\.([A-Za-z_]\w*)\s*=\s*(-?\d+(?:\.\d+)?)\s*(?:#.*)?$")
RE_INSTANCE = re.compile(
    r"^\s*(?:default\s+|define\s+|\$\s*)([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\s*\("
)
RE_ATTRINST = re.compile(r"^\s*self\.([A-Za-z_]\w*)\s*=\s*([A-Za-z_]\w*)\s*\(")
# --- числовое поле на уровне тела класса: `NAME = число` без self. (A4) ---
RE_CLASSVAR = re.compile(r"^(\s*)([A-Za-z_]\w*)\s*=\s*(-?\d+(?:\.\d+)?)\s*(?:#.*)?$")
RE_DICTHEAD = re.compile(r"^\s*default\s+([A-Za-z_]\w*)\s*=\s*\{\s*$")
# --- однострочный dict: `default NAME = { ... }` (A2) ---
RE_DICTONE = re.compile(r"^\s*default\s+([A-Za-z_]\w*)\s*=\s*\{(.*)\}\s*(?:#.*)?$")
# --- начало dict-литерала: `default|define NAME = {` + остаток строки. Покрывает и
#     однострочный, и многострочный вид, в т.ч. с ключами прямо на строке заголовка ---
RE_DICTOPEN = re.compile(r"^\s*(?:default|define)\s+([A-Za-z_]\w*)\s*=\s*\{(.*)$")
RE_DICTNUM = re.compile(r'["\']([A-Za-z_]\w*)["\']\s*:\s*(-?\d+(?:\.\d+)?)')

STAT_KW = (
    "money",
    "gold",
    "cash",
    "coin",
    "dollar",
    "allowance",
    "wallet",
    "currency",
    "premium",
    "love",
    "aff",
    "affection",
    "relation",
    "rel",
    "lust",
    "corrupt",
    "desire",
    "arousal",
    "intimacy",
    "lewd",
    "trust",
    "charm",
    "appeal",
    "reput",
    "fame",
    "hearts",
    "energy",
    "stamina",
    "health",
    "hp",
    "mp",
    "str",
    "dex",
    "int",
    "cha",
    "level",
    "exp",
    "xp",
    "day",
    "week",
    "time",
    "point",
    "score",
    "stat",
    "stage",
    "skill",
    "rank",
    "progress",
)


def tokens(name):
    """Разбить имя на токены по разделителям и camelCase: physicalLevel/physical.level
    -> ['physical','level']. Нужно, чтобы матчить ключевые слова по границе токена,
    а не подстрокой (иначе 'rel' ловит 'irrelevant', 'int' — 'point')."""
    s = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    return [t for t in re.split(r"[^A-Za-z0-9]+", s.lower()) if t]


def _kw_hit(tok):
    """Токен — стат, если равен ключевому слову или (для kw>=3 букв) начинается с него.
    Короткие kw (hp/mp/xp/...) требуют точного совпадения, чтобы не шуметь."""
    for kw in STAT_KW:
        if tok == kw or (len(kw) >= 3 and tok.startswith(kw)):
            return True
    return False


def is_stat(name):
    n = name.lower()
    if n.startswith(
        ("gui.", "config.", "preferences.", "_", "renpy.", "persistent.", "tm_")
    ):
        return False
    return any(_kw_hit(t) for t in tokens(name))


RE_CAND_NAME = re.compile(r'^[A-Za-z_][\w.]*$')
RE_CAND_DICT = re.compile(r'^([A-Za-z_]\w*):\s*(\w+=\S+(?:,\s*\w+=\S+)*)$')
RE_CAND_RPGM = re.compile(r'^(?:var|switch|id)\s+\d+\s*=\s*([\'"])(.*)\1$')


def parse_candidates(text):
    """Строки файла кандидатов -> пары (метка, путь) для таблицы статов.

    Понимает все виды строк отчёта: `имя = значение`, `attr -> инстанс.attr`,
    `dict: k=v, ...` (по паре на ключ), а также строки scan-отчётов Twine/RPG Maker
    (`$x [num] -> State.variables.x`). Заголовки, сигнатуры и пути с
    неразрешённым инстансом (`<Owner>.attr`) пропускаются."""
    out = []
    for line in text.splitlines():
        s = line.split("  // ", 1)[0].strip()  # «  // имя» — подсказка студии, не часть пути
        if not s or s.startswith(("#", "[")):
            continue
        if "->" in s:
            left, path = (p.strip() for p in s.rsplit("->", 1))
            m = RE_CAND_RPGM.match(left)
            label = m.group(2) if m else re.sub(r'\s*\[\w+\]$', "", left).lstrip("$")
            if path and label and not path.startswith("<"):
                out.append((label, path))
            continue
        m = RE_CAND_DICT.match(s)
        if m:
            for item in m.group(2).split(","):
                key = item.split("=", 1)[0].strip()
                out.append((key, '%s["%s"]' % (m.group(1), key)))
            continue
        name = s.split("=", 1)[0].strip() if "=" in s else ""
        if RE_CAND_NAME.match(name):
            out.append((name, name))
    return out


def rel(f, i):
    return os.path.relpath(f, ana_dir(i)).replace("\\", "/")


def extracted_games():
    """Номера игр, реально распакованных в ANA (D:/_ta/game_N)."""
    nums = []
    for d in glob.glob(f"{glob.escape(ANA_BASE)}/game_*"):
        name = os.path.basename(d)
        if os.path.isdir(d) and name[5:].isdigit():
            nums.append(int(name[5:]))
    return sorted(nums)


def dump(i):
    os.makedirs(CAND_DIR, exist_ok=True)
    files = sorted(glob.glob(f"{glob.escape(ana_dir(i))}/**/*.rpy", recursive=True))
    if not files:
        report.warn(
            i, f"нет исходников в {ana_dir(i)} — сначала collect_sources.py {i}"
        )

    flat = {}  # NAME -> value
    inv_hits = []  # (relfile:line, text)
    classes = collections.OrderedDict()  # ClassName -> [attr, ...]
    instances = collections.defaultdict(list)  # ClassName -> [глобал-инстанс, ...]
    attr_inst = collections.defaultdict(list)  # ClassName -> ['OwnerClass.attr', ...]
    dicts = collections.OrderedDict()  # NAME -> [(key, val), ...]

    for f in files:
        if "/tl/" in f.replace("\\", "/"):
            continue  # переводы не нужны
        if os.path.basename(f).startswith("zzz_testmenu_"):
            continue  # файлы самого тест-меню — не статы игры
        try:
            with open(f, encoding="utf-8", errors="ignore") as fh:
                lines = fh.read().splitlines()
        except Exception:
            continue

        cur_class = None
        class_indent = 0
        class_body_indent = None
        in_py = False
        py_indent = 0
        py_body_indent = None
        in_dict = None
        dict_depth = 0
        for ln, line in enumerate(lines, 1):
            stripped = line.strip()
            indent = len(line) - len(line.lstrip())

            # --- многострочный dict: копим ключи по брейс-глубине (A2) ---
            if in_dict is not None:
                for k, v in RE_DICTNUM.findall(line):
                    dicts[in_dict].append((k, v))
                dict_depth += line.count("{") - line.count("}")
                if dict_depth <= 0:
                    in_dict = None
                continue

            # --- выход из класса / python-блока по дедленту ---
            if cur_class and stripped and indent <= class_indent:
                cur_class = None
                class_body_indent = None
            if in_py and stripped and indent <= py_indent:
                in_py = False
                py_body_indent = None
            # базовый отступ тела python-блока = отступ первой строки тела (A1)
            if in_py and stripped and py_body_indent is None and indent > py_indent:
                py_body_indent = indent

            # инвентарь / деньги (в любой строке)
            if RE_INV.search(line) or RE_MONEY.search(line):
                txt = stripped
                if len(txt) > 100:
                    txt = txt[:100] + "…"
                inv_hits.append((f"{rel(f, i)}:{ln}", txt))

            # заголовок python-блока (A1)
            mp = RE_PYHEAD.match(line)
            if mp:
                in_py = True
                py_indent = len(mp.group(1))
                py_body_indent = None

            # заголовок класса
            mc = RE_CLASS.match(line)
            if mc:
                cur_class = mc.group(2)
                class_indent = len(mc.group(1))
                class_body_indent = None
                classes.setdefault(cur_class, [])
                continue

            # плоские глобалы: default/define, $-строка (A1)
            m = RE_FLAT.match(line)
            if m:
                flat.setdefault(m.group(1), m.group(2))
            md_ = RE_DOLLAR.match(line)
            if md_:
                flat.setdefault(md_.group(1), md_.group(2))

            # dict-статы: однострочный (A2) или заголовок многострочного
            mo = RE_DICTOPEN.match(line)
            if mo:
                name, rest = mo.group(1), mo.group(2)
                dicts.setdefault(name, [])
                for k, v in RE_DICTNUM.findall(rest):
                    dicts[name].append((k, v))
                dict_depth = 1 + rest.count("{") - rest.count("}")
                if dict_depth > 0:  # литерал не закрылся на этой строке
                    in_dict = name

            # инстансы классов: default inst = Class(
            mi = RE_INSTANCE.match(line)
            if mi:
                instances[mi.group(2)].append(mi.group(1))

            # тело класса: self.x = число, self.foo = Class(, поле уровня класса (A4)
            if cur_class:
                ms = RE_SELFNUM.match(line)
                if ms and ms.group(1) not in classes[cur_class]:
                    classes[cur_class].append(ms.group(1))
                ma = RE_ATTRINST.match(line)
                if ma:
                    attr_inst[ma.group(2)].append(f"{cur_class}.{ma.group(1)}")
                mcv = RE_CLASSVAR.match(line)
                if mcv and indent > class_indent:
                    if class_body_indent is None:
                        class_body_indent = indent
                    if (
                        indent == class_body_indent
                        and mcv.group(2) not in classes[cur_class]
                    ):
                        classes[cur_class].append(mcv.group(2))

            # тело python-блока: присваивание на базовом уровне (A1)
            if in_py and py_body_indent is not None and indent == py_body_indent:
                mpa = RE_PYASSIGN.match(line)
                if mpa and not mpa.group(2).startswith("self."):
                    flat.setdefault(mpa.group(2), mpa.group(3))

    stat = {k: v for k, v in flat.items() if is_stat(k)}
    other = {k: v for k, v in flat.items() if not is_stat(k)}
    # классы, у которых есть числовые поля (кандидаты в статы через объект)
    stat_classes = {c: a for c, a in classes.items() if a}
    stat_dicts = {n: kv for n, kv in dicts.items() if kv}

    with open(cand_file(i), "w", encoding="utf-8") as o:
        o.write(
            f"# game_{i}: {len(flat)} плоских numeric/bool globals ({len(stat)} stat-like), "
            f"{len(stat_classes)} стат-классов, {len(stat_dicts)} dict-статов, "
            f"{len(inv_hits)} инвентарных сигнатур\n\n"
        )

        o.write("## STAT-LIKE плоские (по ключевым словам)  ->  ('Метка','имя')\n")
        for k in sorted(stat):
            o.write(f"{k} = {stat[k]}\n")

        o.write(
            "\n## ОБЪЕКТНЫЕ СТАТЫ: классы с числовыми полями  ->  ('Метка','инстанс.attr')\n"
        )
        for c in sorted(stat_classes):
            # собираем возможные пути до инстанса класса c
            paths = list(dict.fromkeys(instances.get(c, [])))  # прямые глобалы
            for owner_attr in dict.fromkeys(attr_inst.get(c, [])):
                owner, attr = owner_attr.split(".", 1)
                owner_globals = instances.get(owner, [])
                if owner_globals:
                    for og in dict.fromkeys(owner_globals):
                        paths.append(f"{og}.{attr}")  # напр. state.player_stats
                else:
                    paths.append(f"<{owner}>.{attr}")
            paths = list(dict.fromkeys(paths))
            hint = (" | путь: " + ", ".join(paths)) if paths else " | инстанс не найден"
            o.write(f"[{c}]{hint}\n")
            base = paths[0] if paths else "<инстанс>"
            for a in stat_classes[c]:
                o.write(f"    {a} -> {base}.{a}\n")

        o.write(
            "\n## DICT-СТАТЫ: default NAME = {...числа...}  ->  ('Метка','NAME[\"key\"]')\n"
        )
        for n in sorted(stat_dicts):
            keys = ", ".join(f"{k}={v}" for k, v in stat_dicts[n][:24])
            o.write(f"{n}: {keys}\n")

        o.write("\n## ИНВЕНТАРЬ / ПРЕДМЕТЫ / ДЕНЬГИ (сигнатуры)  ->  для tm_actions\n")
        seen = set()
        for loc, txt in inv_hits:
            if txt in seen:
                continue
            seen.add(txt)
            o.write(f"{loc}:  {txt}\n")

        o.write(f"\n## OTHER плоские ({len(other)}) — первые 120\n")
        for k in sorted(other)[:120]:
            o.write(f"{k} = {other[k]}\n")

    report.info(
        i,
        f"flat={len(flat)} stat={len(stat)} classes={len(stat_classes)} "
        f"dicts={len(stat_dicts)} inv={len(inv_hits)}",
    )
