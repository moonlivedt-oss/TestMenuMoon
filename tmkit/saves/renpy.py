"""Ren'Py: сейвы (.save — zip с pickle «log») и persistent, подпись 8.1+, папка сохранений."""

import io, os, re, sys, zipfile, zlib

from tmkit.saves.core import Doc, _assign, _get_parent, _txt, _walk
from tmkit.saves.renpy_pickle import _Pickler, _Unpickler, _deep, _register_stubs

class RenpyDoc(Doc):
    kind = "renpy"
    title = "Ren'Py"
    depth = 3

    def __init__(self, path, raw=None):
        super().__init__(path)
        raw = raw if raw is not None else open(path, "rb").read()
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            self.entries = [(i, z.read(i.filename)) for i in z.infolist()]
        log = dict((i.filename, d) for i, d in self.entries)["log"]
        self.py2 = b"__builtin__" in log[:4000] or b"copy_reg" in log[:4000]
        enc = "bytes" if self.py2 else "ASCII"
        self.data = _deep(lambda: _Unpickler(io.BytesIO(log), encoding=enc).load())
        self.roots = self.data[0]
        # только значения store: «store.money», «store.girls» …
        self.root = {
            k: v
            for k, v in self.roots.items()
            if _txt(k).startswith("store.")
            and not _txt(k).startswith(("store._", "store.tm_", "store.renpy"))
        }

    def items(self):
        out = []
        for k in sorted(self.root, key=_txt):
            _walk(self.root[k], (k,), _txt(k)[6:], out, self.depth, set())
        return out

    def set(self, path, value):
        if len(path) == 1:
            self.roots[path[0]] = self.root[path[0]] = value
            name = path[0][6:]  # без «store.»
            for rb in self._open_rollbacks():
                st = (rb.__dict__.get("stores") or {}).get(b"store" if isinstance(name, bytes) else "store")
                if isinstance(st, dict) and name in st:
                    st[name] = value
            return
        _assign(self.root, path, value)
        owner, key = _get_parent(self.root, path), path[-1]
        for rb in self._open_rollbacks():
            for ent in rb.__dict__.get("objects") or []:
                if not isinstance(ent, (tuple, list)) or len(ent) < 2 or ent[0] is not owner:
                    continue
                snap = ent[1]
                if isinstance(snap, dict) and key in snap:
                    snap[key] = value
                elif isinstance(snap, list) and isinstance(key, int) and key < len(snap):
                    snap[key] = value

    def _open_rollbacks(self):
        """Записи журнала отката от последней контрольной точки до конца: при загрузке Ren'Py
        откатывает игру к началу текущего оператора, и старые значения берутся отсюда —
        поэтому правка пишется и в них."""
        log = getattr(self.data[1], "__dict__", {}).get("log") or getattr(self.data[1], "__dict__", {}).get(b"log")
        if not isinstance(log, list):
            return []
        out = []
        for rb in reversed(log):
            out.append(rb)
            if getattr(rb, "__dict__", {}).get("checkpoint"):
                break
        return out

    def save(self):
        super().save()
        self.note = renpy_resign(self.path)

    def dump(self):
        added = _register_stubs()
        try:
            buf = io.BytesIO()
            _deep(lambda: _Pickler(buf, protocol=2).dump(self.data))
            log = buf.getvalue()
        finally:
            for mn in added:
                sys.modules.pop(mn, None)
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for info, d in self.entries:
                z.writestr(info, log if info.filename == "log" else d)
        return buf.getvalue()


# Подпись Ren'Py 8.1+ считает Python самой игры (в нём есть ecdsa): данные — файл (сырой
# pickle) или сейв-zip (тогда подписывается его «log»). Вывод — строки «signature <ключ> <подпись>».
_SIGN_PY = r"""
import sys, os, glob, base64, zipfile
base, path, keys = sys.argv[1:4]
for d in glob.glob(os.path.join(base, "lib", "python*")):
    sys.path.insert(0, d)
import ecdsa
data = open(path, "rb").read()
if data[:2] == b"PK":
    data = zipfile.ZipFile(path).read("log")
out = ""
for line in open(keys):
    p = line.split()
    if len(p) >= 2 and p[0] == "signing-key":
        sk = ecdsa.SigningKey.from_der(base64.b64decode(p[1]))
        out += "signature %s %s\n" % (base64.b64encode(sk.verifying_key.to_der()).decode("ascii"),
                                      base64.b64encode(sk.sign(data)).decode("ascii"))
sys.stdout.write(out)
"""

KEYS = os.path.join(os.environ.get("APPDATA", ""), "RenPy", "tokens", "security_keys.txt")


def _sign(base, path):
    """Подпись данных файла path ключом этого ПК. -> (текст подписи, None) или (None, причина)."""
    py = _renpy_python(base) if base else None
    if not os.path.isfile(KEYS) or not py:
        return None, "нет ключа этого ПК или Python игры"
    import subprocess

    try:
        out = subprocess.run(
            [py, "-O", "-c", _SIGN_PY, base, path, KEYS], capture_output=True, timeout=60, cwd=base
        )
    except Exception as e:
        return None, str(e)
    sig = out.stdout.decode("ascii", "replace")
    if out.returncode != 0 or not sig.startswith("signature "):
        return None, out.stderr.decode("utf-8", "replace").strip()[-300:] or "подпись не получилась"
    return sig, None


RENPY_GAME_HINT = {}  # папка сейвов в %APPDATA%/RenPy -> папка игры (заполняет find_saves)


def _renpy_base(save_path):
    """Папка игры Ren'Py (с lib/ и game/) по пути сейва; для сейвов в %APPDATA% — по подсказке."""
    d = os.path.dirname(os.path.abspath(save_path))
    hint = RENPY_GAME_HINT.get(os.path.normcase(d))
    if hint:
        return hint
    for _ in range(4):
        if os.path.isdir(os.path.join(d, "lib")) and os.path.isdir(
            os.path.join(d, "game")
        ):
            return d
        d = os.path.dirname(d)
    return None


def _renpy_python(base):
    import glob

    hits = glob.glob(
        os.path.join(glob.escape(base), "lib", "**", "python.exe"), recursive=True
    )
    hits.sort(key=lambda p: ("x86_64" not in p, "py3" not in p, p))
    return hits[0] if hits else None


def renpy_resign(save_path, game_base=None):
    """Ren'Py 8.1+: подписать сейв ключом этого ПК (%APPDATA%/RenPy/tokens), иначе игра
    спросит, доверять ли ему."""
    with zipfile.ZipFile(save_path) as z:
        if "signatures" not in z.namelist():
            return "подпись не нужна (сейв без подписи)"
    sig, err = _sign(game_base or _renpy_base(save_path), save_path)
    if sig is None:
        return "не переподписан (%s) — игра спросит, доверять ли сейву" % err
    with zipfile.ZipFile(save_path) as z:
        ents = [(i, z.read(i.filename)) for i in z.infolist()]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for info, d in ents:
            z.writestr(info, sig.encode("ascii") if info.filename == "signatures" else d)
    with open(save_path, "wb") as f:
        f.write(buf.getvalue())
    return "переподписан ключом этого компьютера"


# ------------------------------------------------------------------ persistent
class PersistentDoc(Doc):
    """Файл persistent: zlib(pickle объекта Persistent) + в 8.1+ строки подписи после потока.

    Правятся поля persistent (без служебных «_…»). Ren'Py сливает persistent из нескольких
    мест (game/saves и %APPDATA%/RenPy/<игра>) по времени правки каждого поля (_changed) —
    поэтому у изменённых полей время ставится «сейчас», иначе старая копия перебила бы правку.
    Подписанный persistent без новой подписи Ren'Py молча выбросит, поэтому без ключа запись
    отказывается."""

    kind = "persistent"
    title = "Ren'Py persistent"
    depth = 3

    def __init__(self, path, raw=None):
        super().__init__(path)
        raw = raw if raw is not None else open(path, "rb").read()
        do = zlib.decompressobj()
        self.data = do.decompress(raw)
        self.signed = bool(do.unused_data.strip())
        self.py2 = b"__builtin__" in self.data[:4000] or b"copy_reg" in self.data[:4000]
        enc = "bytes" if self.py2 else "ASCII"
        self.obj = _deep(lambda: _Unpickler(io.BytesIO(self.data), encoding=enc).load())
        dd = getattr(self.obj, "__dict__", None)
        if not isinstance(dd, dict):
            raise ValueError("это не persistent Ren'Py")
        self.fields = dd
        self.root = {
            k: v for k, v in dd.items()
            if not _txt(k).startswith("_") and not _txt(k).startswith("tm_")
        }
        self.edited = set()
        self.game_base = None  # папка игры с lib/ (Python для подписи); None — найти по пути

    def items(self):
        out = []
        for k in sorted(self.root, key=_txt):
            _walk(self.root[k], (k,), _txt(k), out, self.depth, set())
        return out

    def set(self, path, value):
        if len(path) == 1:
            self.root[path[0]] = self.fields[path[0]] = value
        else:
            _assign(self.root, path, value)
        self.edited.add(path[0])

    def dump(self):
        import time

        changed = self.fields.get("_changed", self.fields.get(b"_changed"))
        if isinstance(changed, dict):
            now = time.time()
            for k in self.edited:
                dict.__setitem__(changed, k, now)
        added = _register_stubs()
        try:
            buf = io.BytesIO()
            _deep(lambda: _Pickler(buf, protocol=2).dump(self.obj))
        finally:
            for mn in added:
                sys.modules.pop(mn, None)
        data = buf.getvalue()
        out = zlib.compress(data, 3)
        self.note = ""
        if self.signed:
            import tempfile

            fd, tmp = tempfile.mkstemp(suffix=".pickle")
            try:
                with os.fdopen(fd, "wb") as f:
                    f.write(data)
                sig, err = _sign(self.game_base or _renpy_base(self.path), tmp)
            finally:
                os.remove(tmp)
            if sig is None:
                raise ValueError(
                    "persistent подписан, а подписать заново не вышло (%s): Ren'Py выбросил бы "
                    "его целиком — запись отменена" % err
                )
            out += sig.encode("ascii")
            self.note = "переподписан ключом этого компьютера"
        return out


def is_persistent(path, raw):
    """Похоже ли на persistent Ren'Py: имя файла или zlib-поток с pickle протокола 2."""
    if raw[:1] != b"\x78":
        return False
    if os.path.basename(path).lower() == "persistent":
        return True
    try:
        return zlib.decompressobj().decompress(raw[:4096])[:2] == b"\x80\x02"
    except zlib.error:
        return False


_SAVEDIR = re.compile(rb"""save_directory.{0,400}?["']([\w][\w\- .]{1,80})["']""", re.S)


def renpy_save_directory(game_dir):
    """config.save_directory игры: из .rpy, иначе из .rpyc (слоты RPC2 сжаты zlib)."""
    import glob, struct

    files = glob.glob(
        os.path.join(glob.escape(game_dir), "**", "*.rpy"), recursive=True
    )
    files += glob.glob(
        os.path.join(glob.escape(game_dir), "**", "*.rpyc"), recursive=True
    )
    files.sort(
        key=lambda p: ("options" not in os.path.basename(p).lower(), p.endswith("c"))
    )
    for p in files[:400]:
        try:
            raw = open(p, "rb").read()
        except OSError:
            continue
        chunks = [raw]
        if p.endswith("c"):
            chunks = []
            if raw.startswith(b"RENPY RPC2"):
                pos = 10
                while pos + 12 <= len(raw):
                    slot, start, length = struct.unpack("<III", raw[pos : pos + 12])
                    if slot == 0:
                        break
                    pos += 12
                    try:
                        chunks.append(zlib.decompress(raw[start : start + length]))
                    except zlib.error:
                        pass
            else:
                try:
                    chunks.append(zlib.decompress(raw))
                except zlib.error:
                    pass
        for c in chunks:
            m = _SAVEDIR.search(c)
            if m:
                return m.group(1).decode("utf-8", "replace")
    return None
