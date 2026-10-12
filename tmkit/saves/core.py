"""Общее для всех форматов: Item (одно значение), обход дерева, присваивание по пути,
приведение введённого текста к типу значения и базовый документ Doc."""

import os, shutil
from dataclasses import dataclass

SCALARS = (bool, int, float, str, bytes)


@dataclass
class Item:
    path: tuple  # ключи до значения в дереве документа
    label: str  # подпись для человека
    value: object


def _txt(k):
    return k.decode("utf-8", "replace") if isinstance(k, bytes) else str(k)


def _walk(obj, path, label, out, depth, seen):
    """Скаляры дерева (dict / list / объекты-заглушки) как Item; depth — сколько уровней вглубь."""
    if isinstance(obj, SCALARS) or obj is None:
        if obj is not None:
            out.append(Item(path, label, obj))
        return
    if depth < 0 or id(obj) in seen or len(out) > 20000:
        return
    seen.add(id(obj))
    if isinstance(obj, dict):
        kv = list(obj.items())
    elif isinstance(obj, (list, tuple)):
        kv = list(enumerate(obj))
    elif isinstance(getattr(obj, "__dict__", None), dict):
        kv = [(k, v) for k, v in obj.__dict__.items() if not _txt(k).startswith("_tm_")]
        if isinstance(obj, (list, dict)):  # заглушка-контейнер: ещё и элементы
            kv += (
                list(enumerate(obj)) if isinstance(obj, list) else list(dict.items(obj))
            )
    else:
        return
    for k, v in kv:
        if isinstance(obj, tuple) and isinstance(v, SCALARS):
            continue  # кортежи неизменяемы — их скаляры не правим
        sub = label + (
            "[%s]" % k if isinstance(k, int) else ("." if label else "") + _txt(k)
        )
        _walk(v, path + (k,), sub, out, depth - 1, seen)


def _get_parent(root, path):
    o = root
    for k in path[:-1]:
        if isinstance(o, (dict, list)) and not (
            isinstance(o, list) and not isinstance(k, int)
        ):
            try:
                o = o[k]
                continue
            except (KeyError, IndexError, TypeError):
                pass
        o = o.__dict__[k]
    return o


def _assign(root, path, value):
    o = _get_parent(root, path)
    k = path[-1]
    if isinstance(o, list) and isinstance(k, int):
        o[k] = value
    elif isinstance(o, dict) and (k in o or not hasattr(o, "__dict__")):
        dict.__setitem__(o, k, value)
    else:
        o.__dict__[k] = value


def coerce(old, text):
    """Текст из поля ввода -> значение того же типа, что было."""
    if isinstance(old, bool):
        t = str(text).strip().lower()
        if t in ("1", "true", "да", "вкл", "on", "yes"):
            return True
        if t in ("0", "false", "нет", "выкл", "off", "no"):
            return False
        raise ValueError("нужно true / false")
    if isinstance(old, int):
        t = str(text).strip().replace(" ", "")
        try:
            return int(t)  # без float: большие числа (деньги, счётчики) не теряют разряды
        except ValueError:
            return int(float(t.replace(",", ".")))
    if isinstance(old, float):
        return float(str(text).replace(",", "."))
    if isinstance(old, bytes):
        return str(text).encode("utf-8")
    return str(text)


def _backup(path):
    bak = path + ".tm_bak"
    if os.path.isfile(path) and not os.path.exists(bak):
        shutil.copy2(path, bak)


class Doc:
    kind = "?"
    title = ""
    depth = 6

    def __init__(self, path):
        self.path = path
        self.root = None
        self.names = {}  # подписи: путь -> понятное имя (RPG Maker: имена переменных)

    def items(self):
        out = []
        _walk(self.root, (), "", out, self.depth, set())
        for it in out:
            nice = self.names.get(it.path)
            if nice:
                it.label = nice + "   (" + it.label + ")"
        return out

    def set(self, path, value):
        _assign(self.root, path, value)

    def save(self):
        _backup(self.path)
        data = self.dump()
        with open(self.path, "wb") as f:
            f.write(data)
