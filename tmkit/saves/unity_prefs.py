"""Unity PlayerPrefs в реестре: HKCU\\Software\\<компания>\\<игра>."""

import json, os, re

from tmkit.saves.core import Doc, Item

_HASH = re.compile(r"_h\d+$")


class PrefsDoc(Doc):
    kind = "prefs"
    title = "Unity PlayerPrefs"

    def __init__(self, company, product):
        super().__init__("HKCU\\Software\\%s\\%s" % (company, product))
        import winreg

        self.key = r"Software\%s\%s" % (company, product)
        self.product = product
        self.raw = {}
        self.root = {}
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, self.key) as k:
            i = 0
            while True:
                try:
                    n, v, t = winreg.EnumValue(k, i)
                except OSError:
                    break
                i += 1
                self.raw[n] = (v, t)
                val = _prefs_value(v, t)
                if val is not None:
                    self.root[n] = val

    def items(self):
        return [
            Item((n,), _HASH.sub("", n), v)
            for n, v in sorted(self.root.items(), key=lambda x: x[0].lower())
            if not n.startswith(
                ("unity.", "unity_connect", "Screenmanager", "UnitySelectMonitor")
            )
        ]

    def set(self, path, value):
        self.root[path[0]] = value

    def save(self):
        import winreg
        from tmkit.paths import BUILD

        os.makedirs(BUILD, exist_ok=True)
        bak = os.path.join(
            BUILD, "tm_prefs_%s.json" % re.sub(r"[^\w-]+", "_", self.product)
        )
        if not os.path.exists(bak):
            with open(bak, "w", encoding="utf-8") as f:
                json.dump(
                    {
                        n: [v.hex() if isinstance(v, bytes) else v, t]
                        for n, (v, t) in self.raw.items()
                    },
                    f,
                    ensure_ascii=False,
                    indent=1,
                )
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, self.key, 0, winreg.KEY_SET_VALUE
        ) as k:
            for n, val in self.root.items():
                v, t = self.raw[n]
                if _prefs_value(v, t) == val:
                    continue
                nv, nt = _prefs_raw(val, t)
                winreg.SetValueEx(k, n, 0, nt, nv)
                self.raw[n] = (nv, nt)


def _prefs_value(v, t):
    import winreg

    if t == winreg.REG_DWORD:
        return int(v) - (1 << 32) if v >= 1 << 31 else int(v)
    if t == winreg.REG_QWORD:
        import struct

        return struct.unpack("<d", struct.pack("<Q", v))[0]
    if t == winreg.REG_BINARY and isinstance(v, bytes):
        if v.endswith(b"\0"):
            return v[:-1].decode("utf-8", "replace")
        if len(v) == 8:
            import struct

            return struct.unpack("<d", v)[0]
    return None


def _prefs_raw(val, t):
    import struct, winreg

    if isinstance(val, str):
        return val.encode("utf-8") + b"\0", winreg.REG_BINARY
    if t == winreg.REG_DWORD:
        return int(val) & 0xFFFFFFFF, t
    if t == winreg.REG_QWORD:
        return struct.unpack("<Q", struct.pack("<d", float(val)))[0], t
    return struct.pack("<d", float(val)), winreg.REG_BINARY


def unity_names(game_dir):
    """(компания, игра) из <игра>_Data/app.info."""
    for d in os.listdir(game_dir):
        p = os.path.join(game_dir, d, "app.info")
        if d.endswith("_Data") and os.path.isfile(p):
            with open(p, encoding="utf-8", errors="replace") as f:
                lines = f.read().splitlines()
            if len(lines) >= 2:
                return lines[0].strip(), lines[1].strip()
    return None
