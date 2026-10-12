"""Снимки сейвов и сравнение: что изменилось между двумя состояниями игры.

Сохранил игру до сцены — «Снимок», после сцены — «Сравнить со снимком»: видно, какие
переменные сцена поменяла. Или два файла сейва напрямую (save_a и save_b).

    snap = snapshot(doc)                  # {ключ: (подпись, значение)}
    changes = diff(snap, snapshot(doc2))  # [Change(label, before, after, kind)]
Снимок можно сохранить на диск (save_snap / load_snap) — в build/save_snaps/.
"""

import hashlib
import json
import os
from dataclasses import dataclass

MISSING = object()


@dataclass
class Change:
    label: str
    before: object  # MISSING — значения не было
    after: object  # MISSING — значение пропало
    kind: str  # 'changed' | 'added' | 'removed'


def _plain(v):
    """Значение, которое переживёт JSON (bytes py2-сейвов -> текст)."""
    if isinstance(v, bytes):
        return v.decode("utf-8", "replace")
    return v


def _key(path):
    return json.dumps([_plain(p) if not isinstance(p, (int, float, bool)) else p for p in path], ensure_ascii=False)


def snapshot(doc):
    """{ключ пути: (подпись, значение)} — все значения документа."""
    return {_key(it.path): (it.label, _plain(it.value)) for it in doc.items()}


def diff(old, new):
    """Изменения от снимка old к снимку new: сначала изменённые, потом новые и пропавшие."""
    out = []
    for k, (label, v) in new.items():
        if k not in old:
            out.append(Change(label, MISSING, v, "added"))
        elif old[k][1] != v or type(old[k][1]) is not type(v):
            out.append(Change(label, old[k][1], v, "changed"))
    for k, (label, v) in old.items():
        if k not in new:
            out.append(Change(label, v, MISSING, "removed"))
    order = {"changed": 0, "added": 1, "removed": 2}
    out.sort(key=lambda c: (order[c.kind], c.label.lower()))
    return out


def text(v):
    if v is MISSING:
        return "—"
    if v is True:
        return "true"
    if v is False:
        return "false"
    return str(v)


# ------------------------------------------------------------------ снимки на диске
def _snap_path(target):
    from tmkit.paths import BUILD

    h = hashlib.sha1(str(target).encode("utf-8")).hexdigest()[:16]
    return os.path.join(BUILD, "save_snaps", h + ".json")


def save_snap(target, snap):
    p = _snap_path(target)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump({"target": str(target), "values": snap}, f, ensure_ascii=False)
    return p


def load_snap(target):
    """Снимок цели с диска или None."""
    try:
        with open(_snap_path(target), encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, ValueError):
        return None
    return {k: tuple(v) for k, v in data.get("values", {}).items()}
