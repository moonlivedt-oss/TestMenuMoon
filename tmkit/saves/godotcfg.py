"""Godot ConfigFile: [секция] ключ=значение; правятся только простые значения."""

import json, re

from tmkit.saves.core import Doc, Item

_CFG_LINE = re.compile(r"^(\s*)([^=\[;#][^=]*?)(\s*=\s*)(.*?)\s*$")


class GodotCfgDoc(Doc):
    kind = "godotcfg"
    title = "Godot ConfigFile"

    def __init__(self, path, raw=None):
        super().__init__(path)
        self.lines = (
            (raw if raw is not None else open(path, "rb").read())
            .decode("utf-8-sig")
            .split("\n")
        )
        self.root = {}
        sec = ""
        for i, ln in enumerate(self.lines):
            s = ln.strip()
            if s.startswith("[") and s.endswith("]"):
                sec = s[1:-1]
                continue
            m = _CFG_LINE.match(ln)
            if not m:
                continue
            v = _cfg_value(m.group(4))
            if v is not None:
                self.root.setdefault(sec, {})[m.group(2)] = v
                self.root[sec].setdefault("\0lines", {})[m.group(2)] = i

    def items(self):
        out = []
        for sec, kv in self.root.items():
            for k, v in kv.items():
                if k != "\0lines":
                    out.append(Item((sec, k), (sec + "/" if sec else "") + k, v))
        return out

    def set(self, path, value):
        sec, k = path
        self.root[sec][k] = value
        i = self.root[sec]["\0lines"][k]
        m = _CFG_LINE.match(self.lines[i])
        self.lines[i] = m.group(1) + m.group(2) + m.group(3) + _cfg_text(value)

    def dump(self):
        return "\n".join(self.lines).encode("utf-8")


def _cfg_value(t):
    if t in ("true", "false"):
        return t == "true"
    if re.fullmatch(r"-?\d+", t):
        return int(t)
    if re.fullmatch(r"-?\d+\.\d*(e-?\d+)?|-?\d+e-?\d+", t):
        return float(t)
    if len(t) >= 2 and t[0] == '"' and t[-1] == '"':
        try:
            return json.loads(t)
        except ValueError:
            return None
    return None  # Vector2(…), массивы и прочее — не трогаем


def _cfg_text(v):
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, (int, float)):
        return repr(v)
    return json.dumps(v, ensure_ascii=False)
