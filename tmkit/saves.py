"""Сохранения игр: найти, открыть, показать значения плоским списком, записать обратно.

Форматы (определяются по содержимому, не по расширению):
  rpgmv    — RPG Maker MV .rpgsave: LZString.compressToBase64(JSON)
  rpgmz    — RPG Maker MZ .rmmzsave: zlib(JSON), байты записаны как символы в UTF-8
  renpy    — Ren'Py .save: zip, внутри pickle «log» = (roots, журнал отката); правим roots —
             значения store на момент сохранения (py2- и py3-игры, протокол 2)
  json     — любой JSON (Unity LocalLow, Godot user://, Easy Save без шифрования …)
  godotcfg — ConfigFile Godot ([секция] ключ=значение)
  prefs    — Unity PlayerPrefs в реестре HKCU\\Software\\<компания>\\<игра>

Документ: doc.items() -> [Item(path, label, value)], doc.set(path, value), doc.save().
Перед первой записью рядом остаётся копия «<файл>.tm_bak» (для реестра — tm_prefs_<игра>.json
в build/).
"""

import io, json, os, pickle, re, shutil, sys, types, zipfile, zlib
from dataclasses import dataclass

from tmkit import lzstring

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


# ------------------------------------------------------------------ JSON и RPG Maker
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


# ------------------------------------------------------------------ Godot ConfigFile
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


# ------------------------------------------------------------------ Ren'Py
# Классы игры и движка в студии не загрузить, поэтому pickle разбирается на заглушки:
# каждая запоминает модуль, имя, аргументы и состояние и сериализуется обратно так же.
_STUBS = {}
_SAFE = {
    ("builtins", n)
    for n in (
        "set",
        "frozenset",
        "list",
        "dict",
        "tuple",
        "object",
        "bytes",
        "bytearray",
        "complex",
        "slice",
        "range",
        "int",
        "float",
        "str",
        "bool",
    )
}
_SAFE |= {
    ("copyreg", "_reconstructor"),
    ("copyreg", "__newobj__"),
    ("_codecs", "encode"),
    ("collections", "OrderedDict"),
    ("collections", "defaultdict"),
    ("collections", "deque"),
    ("datetime", "datetime"),
    ("datetime", "date"),
    ("datetime", "time"),
    ("datetime", "timedelta"),
    ("decimal", "Decimal"),
    ("fractions", "Fraction"),
}


def _stub_state(o):
    """Состояние заглушки в той же форме, в какой оно пришло из сейва."""
    dd = o.__dict__
    if "_tm_state" in dd:
        return dd["_tm_state"]
    shape = dd.get("_tm_shape")
    if shape:
        _k, none_dict, dkeys, skeys = shape
        return (None if none_dict else {k: dd[k] for k in dkeys if k in dd}, {k: dd[k] for k in skeys if k in dd})
    d = {k: v for k, v in dd.items() if not _txt(k).startswith("_tm_")}
    return d or None


def _stub(module, name):
    key = (module, name)
    if key in _STUBS:
        return _STUBS[key]
    base = (
        list
        if "List" in name
        else dict
        if "Dict" in name
        else set
        if "Set" in name
        else object
    )

    def __new__(cls, *args, **kw):
        o = base.__new__(cls) if base is not object else object.__new__(cls)
        o.__dict__["_tm_args"] = args
        return o

    def __init__(self, *args, **kw):
        self.__dict__["_tm_call"] = True
        if base is set and args:
            set.update(self, args[0])

    def __setstate__(self, state):
        # запоминаем форму состояния: dict, (dict|None, слоты) или что-то своё — так же и запишем
        if (
            isinstance(state, tuple)
            and len(state) == 2
            and (state[0] is None or isinstance(state[0], dict))
            and isinstance(state[1], dict)
        ):
            self.__dict__["_tm_shape"] = ("slots", state[0] is None,
                                          tuple((state[0] or {}).keys()), tuple(state[1].keys()))
            self.__dict__.update(state[0] or {})
            self.__dict__.update(state[1])
        elif isinstance(state, dict):
            self.__dict__.update(state)
        elif state is not None:
            self.__dict__["_tm_state"] = state

    def __reduce_ex__(self, proto):
        state = _stub_state(self)
        if base is set:
            return (type(self), (list(self),), state)
        li = iter(self) if base is list else None
        di = iter(dict.items(self)) if base is dict else None
        if self.__dict__.get("_tm_call"):
            return (type(self), self.__dict__.get("_tm_args", ()), state, li, di)
        import copyreg

        return (
            copyreg.__newobj__,
            (type(self),) + tuple(self.__dict__.get("_tm_args", ())),
            state,
            li,
            di,
        )

    cls = type(
        name.split(".")[-1],
        (base,),
        {
            "__new__": __new__,
            "__init__": __init__,
            "__setstate__": __setstate__,
            "__reduce_ex__": __reduce_ex__,
            "__module__": module,
            "__qualname__": name,
            "_tm_stub": True,  # метка для _Unpickler._old / _Pickler.save (старые классы py2)
        },
    )
    if base is dict:
        cls.__hash__ = object.__hash__
    if base in (list, set):
        cls.__hash__ = object.__hash__
    _STUBS[key] = cls
    return cls


class _Call(dict):
    """Несостоявшийся вызов из pickle: func(*args) — при записи тот же REDUCE (с элементами,
    если pickle потом наполнял результат как словарь или список)."""

    def __init__(self, func, args):
        super().__init__()
        self.func, self.args, self.items_list = func, args, []

    def __call__(self, *a, **k):
        return None

    def append(self, x):
        self.items_list.append(x)

    def extend(self, xs):
        self.items_list.extend(xs)

    def __setstate__(self, state):
        self.state = state

    __hash__ = object.__hash__

    def __reduce_ex__(self, proto):
        return (self.func, tuple(self.args), getattr(self, "state", None),
                iter(self.items_list) if self.items_list else None,
                iter(dict.items(self)) if len(self) else None)


def _deep(fn, *args):
    """pickle на чистом Python рекурсивен, а журнал Ren'Py глубокий (цепочки узлов):
    выполняем в потоке с большим стеком и высоким пределом рекурсии."""
    import threading

    box = {}

    def run():
        old = sys.getrecursionlimit()
        sys.setrecursionlimit(200000)
        try:
            box["v"] = fn(*args)
        except BaseException as e:
            box["e"] = e
        finally:
            sys.setrecursionlimit(old)

    prev = threading.stack_size(256 * 1024 * 1024 - 4096)
    try:
        t = threading.Thread(target=run)
        t.start()
        t.join()
    finally:
        threading.stack_size(prev)
    if "e" in box:
        raise box["e"]
    return box["v"]


class _Unpickler(pickle._Unpickler):
    """Чистый Python-разборщик: свои find_class и пометка объектов старых классов py2 (OBJ/INST)."""

    dispatch = dict(pickle._Unpickler.dispatch)

    def find_class(self, module, name):
        m = {"__builtin__": "builtins", "copy_reg": "copyreg"}.get(module, module)
        if (m, name) in _SAFE:
            return super().find_class(m, name)
        return _stub(module, name)

    def _old(self, op):
        op(self)
        o = self.stack[-1]
        if getattr(type(o), "_tm_stub", False):
            o.__dict__["_tm_old"] = True

    def _reduce(self):
        # вызов, который в студии не выполнить (метод объекта игры как фабрика defaultdict
        # и т.п.), — запоминаем как есть и при записи повторяем тот же REDUCE
        args = self.stack.pop()
        func = self.stack[-1]
        try:
            self.stack[-1] = func(*args)
        except Exception:
            self.stack[-1] = _Call(func, args)

    dispatch[pickle.REDUCE[0]] = _reduce
    dispatch[pickle.OBJ[0]] = lambda self: self._old(pickle._Unpickler.load_obj)
    dispatch[pickle.INST[0]] = lambda self: self._old(pickle._Unpickler.load_inst)


class _Pickler(pickle._Pickler):
    """Объект старого класса py2 пишется снова через OBJ: у таких классов нет __new__."""

    def save(self, obj, save_persistent_id=True):
        if getattr(type(obj), "_tm_stub", False) and obj.__dict__.get("_tm_old"):
            x = self.memo.get(id(obj))
            if x is not None:
                self.write(self.get(x[0]))
                return
            self.write(pickle.MARK)
            self.save(type(obj))
            self.write(pickle.OBJ)
            self.memoize(obj)
            state = _stub_state(obj) or {}
            self.save(state)
            self.write(pickle.BUILD)
            return
        super().save(obj, save_persistent_id)


def _register_stubs():
    """Модули-заглушки в sys.modules: pickle при записи проверяет, что класс находится по имени."""
    added = []
    for (module, name), cls in _STUBS.items():
        parts = module.split(".")
        for i in range(1, len(parts) + 1):
            mn = ".".join(parts[:i])
            if mn not in sys.modules:
                sys.modules[mn] = types.ModuleType(mn)
                added.append(mn)
        setattr(sys.modules[module], name.split(".")[-1], cls)
    return added


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


_SIGN_PY = r"""
import sys, os, glob, base64, zipfile
base, save, keys = sys.argv[1:4]
for d in glob.glob(os.path.join(base, "lib", "python*")):
    sys.path.insert(0, d)
import ecdsa
log = zipfile.ZipFile(save).read("log")
out = ""
for line in open(keys):
    p = line.split()
    if len(p) >= 2 and p[0] == "signing-key":
        sk = ecdsa.SigningKey.from_der(base64.b64decode(p[1]))
        out += "signature %s %s\n" % (base64.b64encode(sk.verifying_key.to_der()).decode("ascii"),
                                      base64.b64encode(sk.sign(log)).decode("ascii"))
sys.stdout.write(out)
"""

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
    спросит, доверять ли ему. Подпись считает Python самой игры (в нём есть ecdsa)."""
    with zipfile.ZipFile(save_path) as z:
        if "signatures" not in z.namelist():
            return "подпись не нужна (сейв без подписи)"
    keys = os.path.join(
        os.environ.get("APPDATA", ""), "RenPy", "tokens", "security_keys.txt"
    )
    base = game_base or _renpy_base(save_path)
    py = _renpy_python(base) if base else None
    if not os.path.isfile(keys) or not py:
        return "не переподписан (нет ключа или Python игры) — игра спросит, доверять ли сейву"
    import subprocess

    try:
        out = subprocess.run(
            [py, "-O", "-c", _SIGN_PY, base, save_path, keys],
            capture_output=True,
            timeout=60,
            cwd=base,
        )
    except Exception as e:
        return "не переподписан: %s" % e
    sig = out.stdout.decode("ascii", "replace")
    if out.returncode != 0 or not sig.startswith("signature "):
        return (
            "не переподписан: " + out.stderr.decode("utf-8", "replace").strip()[-300:]
        )
    with zipfile.ZipFile(save_path) as z:
        ents = [(i, z.read(i.filename)) for i in z.infolist()]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for info, d in ents:
            z.writestr(
                info, sig.encode("ascii") if info.filename == "signatures" else d
            )
    with open(save_path, "wb") as f:
        f.write(buf.getvalue())
    return "переподписан ключом этого компьютера"


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


# ------------------------------------------------------------------ Unity PlayerPrefs (реестр)
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


# ------------------------------------------------------------------ открыть и найти
def open_save(path):
    """Документ по содержимому файла. ValueError — формат не распознан."""
    raw = open(path, "rb").read()
    if raw[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            if "log" in z.namelist():
                return RenpyDoc(path, raw)
    head = raw.lstrip(b"\xef\xbb\xbf \t\r\n")[:1]
    if head in (b"{", b"["):
        try:
            return JsonDoc(path, raw)
        except ValueError:
            pass
    if re.fullmatch(rb"[A-Za-z0-9+/=\s]+", raw[:4096]):
        try:
            text = lzstring.decompress_from_base64(raw.decode("ascii"))
            if text and text.lstrip()[:1] in "{[":
                return RpgMvDoc(path, raw)
        except Exception:
            pass
    try:
        z = raw.decode("utf-8").encode("latin-1")
        if z[:1] == b"\x78":
            zlib.decompress(z)
            return RpgMzDoc(path, raw)
    except Exception:
        pass
    try:
        text = raw.decode("utf-8-sig")
        if re.search(r"^\[[^\]]+\]\s*$", text, re.M) and "=" in text:
            return GodotCfgDoc(path, raw)
    except UnicodeDecodeError:
        pass
    raise ValueError("формат не распознан (двоичный или зашифрованный сейв)")


SAVE_EXT = (
    ".save",
    ".rpgsave",
    ".rmmzsave",
    ".json",
    ".sav",
    ".dat",
    ".cfg",
    ".txt",
    ".es3",
    ".data",
)


def _files(d, exts=SAVE_EXT, depth=2):
    out = []
    if not os.path.isdir(d):
        return out
    for root, dirs, files in os.walk(d):
        if root[len(d) :].count(os.sep) >= depth:
            dirs[:] = []
        for f in files:
            if (
                f.lower().endswith(exts)
                and not f.endswith(".tm_bak")
                and f != "tm_state.json"
            ):
                out.append(os.path.join(root, f))
    return out


def _norm(s):
    return re.sub(r"[^a-z0-9]", "", s.lower())


def find_saves(game_dir, engine_key):
    """Где лежат сохранения игры -> [(подпись, путь | ("prefs", компания, игра))]."""
    res = []
    appdata = os.environ.get("APPDATA", "")
    local_low = os.path.join(
        os.path.dirname(os.environ.get("LOCALAPPDATA", "")), "LocalLow"
    )
    base = (
        os.path.dirname(game_dir)
        if os.path.basename(game_dir).lower() == "game"
        else game_dir
    )
    if engine_key == "renpy":
        for d in (os.path.join(base, "game", "saves"), os.path.join(game_dir, "saves")):
            res += [("в папке игры", p) for p in _files(d, (".save",), 0)]
        gd = os.path.join(base, "game")
        sd = renpy_save_directory(gd if os.path.isdir(gd) else game_dir)
        rp = os.path.join(appdata, "RenPy")
        dirs = [sd] if sd and os.path.isdir(os.path.join(rp, sd)) else []
        if not dirs and os.path.isdir(rp):
            # save_directory в архиве .rpa — сверяем имена папок с именем .exe / .py игры
            keys = {_norm(os.path.splitext(f)[0])[:8] for f in os.listdir(base)
                    if f.lower().endswith((".exe", ".py")) and not f.lower().startswith(("python", "unins"))}
            keys = {k for k in keys if len(k) >= 4}
            dirs = [d for d in os.listdir(rp) if any(_norm(d).startswith(k) for k in keys)]
        for d in dirs:
            RENPY_GAME_HINT[os.path.normcase(os.path.join(rp, d))] = base
            res += [("RenPy/" + d, p) for p in _files(os.path.join(rp, d), (".save",), 0)]
    elif engine_key == "rpgmaker":
        for sub in ("save", os.path.join("www", "save")):
            res += [
                ("save", p)
                for p in _files(os.path.join(base, sub), (".rpgsave", ".rmmzsave"), 0)
            ]
    elif engine_key == "unity":
        names = unity_names(base)
        if names:
            res.append(("PlayerPrefs (реестр)", ("prefs",) + names))
            res += [("LocalLow", p) for p in _files(os.path.join(local_low, *names))]
    elif engine_key == "godot":
        key = _norm(os.path.basename(base))[:6]
        for root in (os.path.join(appdata, "Godot", "app_userdata"), appdata):
            if not key or not os.path.isdir(root):
                continue
            for d in os.listdir(root):
                if key in _norm(d) and os.path.isdir(os.path.join(root, d)):
                    res += [(d, p) for p in _files(os.path.join(root, d))]
    seen, out = set(), []
    for lab, p in res:
        k = p if isinstance(p, tuple) else os.path.normcase(os.path.abspath(p))
        if k not in seen:
            seen.add(k)
            out.append((lab, p))
    return out


def open_any(target):
    if isinstance(target, tuple) and target[0] == "prefs":
        return PrefsDoc(target[1], target[2])
    return open_save(target)
