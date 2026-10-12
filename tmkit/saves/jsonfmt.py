"""JSON (Unity LocalLow, Godot user://, Easy Save без шифрования) и RPG Maker MV/MZ."""

import json, os, zlib

from tmkit import lzstring
from tmkit.saves.core import Doc

class JsonDoc(Doc):
    kind = "json"
    title = "JSON"

    def __init__(self, path, raw=None):
        super().__init__(path)
        text = (raw if raw is not None else open(path, "rb").read()).decode("utf-8-sig")
        self.compact = "\n" not in text.strip()
        self.root = json.loads(text)

    def text(self):
        if self.compact:
            return json.dumps(self.root, ensure_ascii=False, separators=(",", ":"))
        return json.dumps(self.root, ensure_ascii=False, indent=2)

    def dump(self):
        return self.text().encode("utf-8")


class RpgMvDoc(JsonDoc):
    kind = "rpgmv"
    title = "RPG Maker MV"

    def __init__(self, path, raw=None):
        raw = raw if raw is not None else open(path, "rb").read()
        text = lzstring.decompress_from_base64(raw.decode("ascii").strip())
        super().__init__(path, text.encode("utf-8"))
        self.compact = True
        _rpgm_names(self)

    def dump(self):
        return lzstring.compress_to_base64(self.text()).encode("ascii")


class RpgMzDoc(JsonDoc):
    kind = "rpgmz"
    title = "RPG Maker MZ"

    def __init__(self, path, raw=None):
        raw = raw if raw is not None else open(path, "rb").read()
        z = raw.decode("utf-8").encode("latin-1")  # pako to:"string" -> fs в UTF-8
        super().__init__(path, zlib.decompress(z))
        self.compact = True
        _rpgm_names(self)

    def dump(self):
        z = zlib.compress(self.text().encode("utf-8"), 1)
        return z.decode("latin-1").encode("utf-8")


def _rpgm_data_dir(save_path):
    d = os.path.dirname(os.path.dirname(os.path.abspath(save_path)))
    for sub in ("data", os.path.join("www", "data")):
        if os.path.isfile(os.path.join(d, sub, "System.json")):
            return os.path.join(d, sub)
    return None


def _rpgm_names(doc):
    """Имена переменных, переключателей, предметов и героев из data/*.json игры."""
    r = doc.root if isinstance(doc.root, dict) else {}
    dd = _rpgm_data_dir(doc.path)

    def load(name):
        try:
            with open(os.path.join(dd, name), encoding="utf-8-sig") as f:
                return json.load(f)
        except Exception:
            return None

    system = load("System.json") if dd else None
    names = doc.names
    if isinstance(r.get("party"), dict):
        names[("party", "_gold")] = "Золото"
    for key, label, src in (
        ("variables", "Переменная", "variables"),
        ("switches", "Переключатель", "switches"),
    ):
        data = (r.get(key) or {}).get("_data") if isinstance(r.get(key), dict) else None
        if isinstance(data, dict):  # JsonEx MV: массив как {"@a": [...]}
            data = data.get("@a")
        if not isinstance(data, list):
            continue
        sub = ("_data", "@a") if isinstance(r[key].get("_data"), dict) else ("_data",)
        nm = (system or {}).get(src) or []
        for i in range(len(data)):
            n = nm[i] if i < len(nm) and nm[i] else ""
            names[(key,) + sub + (i,)] = "%s #%d%s" % (label, i, (" " + n) if n else "")
    for key, fname, label in (
        ("_items", "Items.json", "Предмет"),
        ("_weapons", "Weapons.json", "Оружие"),
        ("_armors", "Armors.json", "Броня"),
    ):
        party = r.get("party")
        inv = party.get(key) if isinstance(party, dict) else None
        if not isinstance(inv, dict):
            continue
        data = load(fname) if dd else None
        for k in inv:
            try:
                n = data[int(k)]["name"] if data else ""
            except Exception:
                n = ""
            names[("party", key, k)] = "%s #%s%s" % (label, k, (" " + n) if n else "")
    actors = load("Actors.json") if dd else None
    acts = (
        (r.get("actors") or {}).get("_data")
        if isinstance(r.get("actors"), dict)
        else None
    )
    if isinstance(acts, dict):
        acts = acts.get("@a")
    if isinstance(acts, list):
        sub = (
            ("_data", "@a")
            if isinstance(r["actors"].get("_data"), dict)
            else ("_data",)
        )
        for i, a in enumerate(acts):
            if not isinstance(a, dict):
                continue
            n = a.get("_name") or (
                actors[i]["name"]
                if actors and i < len(actors) and actors[i]
                else "#%d" % i
            )
            for f, t in (
                ("_level", "уровень"),
                ("_hp", "HP"),
                ("_mp", "MP"),
                ("_tp", "TP"),
            ):
                if f in a:
                    names[("actors",) + sub + (i, f)] = "%s: %s" % (n, t)
