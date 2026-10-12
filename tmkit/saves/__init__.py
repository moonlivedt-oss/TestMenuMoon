"""Сохранения игр: найти, открыть, показать значения плоским списком, записать обратно.

Форматы (определяются по содержимому, не по расширению):
  rpgmv    — RPG Maker MV .rpgsave: LZString.compressToBase64(JSON)
  rpgmz    — RPG Maker MZ .rmmzsave: zlib(JSON), байты записаны как символы в UTF-8
  renpy    — Ren'Py .save: zip, внутри pickle «log» = (roots, журнал отката); правим roots —
             значения store на момент сохранения (py2- и py3-игры, протокол 2)
  persistent — Ren'Py persistent: zlib(pickle) + подпись 8.1+ (переподписывается)
  json     — любой JSON (Unity LocalLow, Godot user://, Easy Save без шифрования …)
  godotcfg — ConfigFile Godot ([секция] ключ=значение)
  prefs    — Unity PlayerPrefs в реестре HKCU\\Software\\<компания>\\<игра>

Модули пакета: core (Item, Doc, приведение типов), jsonfmt (JSON, RPG Maker), godotcfg,
renpy_pickle (pickle на заглушках), renpy (сейвы, persistent, подпись), unity_prefs (реестр).

Документ: doc.items() -> [Item(path, label, value)], doc.set(path, value), doc.save().
Перед первой записью рядом остаётся копия «<файл>.tm_bak» (для реестра — tm_prefs_<игра>.json
в build/).
"""

from tmkit.saves.core import SCALARS, Doc, Item, _assign, _get_parent, _txt, _walk, coerce  # noqa: F401
from tmkit.saves.jsonfmt import JsonDoc, RpgMvDoc, RpgMzDoc  # noqa: F401
from tmkit.saves.godotcfg import GodotCfgDoc  # noqa: F401
from tmkit.saves.renpy_pickle import _Pickler, _Unpickler, _deep, _register_stubs, _stub  # noqa: F401
from tmkit.saves.renpy import (  # noqa: F401
    RENPY_GAME_HINT, PersistentDoc, RenpyDoc, is_persistent, renpy_resign, renpy_save_directory,
)
from tmkit.saves.unity_prefs import PrefsDoc, unity_names  # noqa: F401

import io, os, re, zipfile, zlib

from tmkit import lzstring


def open_save(path):
    """Документ по содержимому файла. ValueError — формат не распознан."""
    raw = open(path, "rb").read()
    if raw[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(raw)) as z:
            if "log" in z.namelist():
                return RenpyDoc(path, raw)
    if is_persistent(path, raw):
        return PersistentDoc(path, raw)
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


def _persistent_in(d, label):
    p = os.path.join(d, "persistent")
    return [(label, p)] if os.path.isfile(p) else []


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
            res += _persistent_in(d, "persistent в папке игры")
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
            res += _persistent_in(os.path.join(rp, d), "persistent RenPy/" + d)
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
