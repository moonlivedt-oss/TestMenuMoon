#!/usr/bin/env python3
"""Минимальный распаковщик RPA-2.0/3.0 (без зависимостей).

Используется collect_sources: извлекает из .rpa только скрипты (scripts_only).
Архив — чужие данные, поэтому индекс читается ограниченным unpickler'ом (никаких
классов/функций из pickle), а имена файлов не могут выйти за пределы outdir.
"""

import io, sys, os, zlib, pickle

SCRIPT_EXT = (".rpyc", ".rpy", ".rpymc", ".rpym")


def _long(path):
    """Windows extended-length path — обойти MAX_PATH (260)."""
    if os.name == "nt":
        ap = os.path.abspath(path).replace("/", "\\")
        if not ap.startswith("\\\\?\\"):
            ap = "\\\\?\\" + ap
        return ap
    return path


# Ren'Py 8 пишет индекс протоколом 2 из py3: байтовый префикс записи кодируется
# через эти безобидные глобалы — без них не читается ни один py3-архив.
_INDEX_GLOBALS = {
    ("_codecs", "encode"),
    ("__builtin__", "bytes"),
    ("builtins", "bytes"),
}


class _IndexUnpickler(pickle.Unpickler):
    """Индекс RPA — только dict/list/tuple/str/bytes/int. Любая другая ссылка на
    глобал в pickle — признак подложенного архива (исполнение кода при распаковке)."""

    def find_class(self, module, name):
        if (module, name) in _INDEX_GLOBALS:
            return super().find_class(module, name)
        raise pickle.UnpicklingError(
            "RPA index: запрещённый объект %s.%s" % (module, name)
        )


def _load_index(blob):
    # encoding="bytes": индекс из py2-архива хранит имена байтами (не-ASCII имена
    # с дефолтным ASCII-декодированием роняли весь архив)
    return _IndexUnpickler(io.BytesIO(zlib.decompress(blob)), encoding="bytes").load()


def _text(name):
    return name.decode("utf-8", "replace") if isinstance(name, bytes) else name


def _safe_rel(name):
    """Относительный путь внутри outdir или None (абсолютный / с '..' / с диском)."""
    rel = os.path.normpath(name.replace("\\", "/"))
    if os.path.isabs(rel) or rel.startswith("..") or ":" in rel or rel in ("", "."):
        return None
    return rel


def extract(rpa_path, outdir, scripts_only=False):
    """Распаковать архив в outdir. Возвращает число извлечённых файлов."""
    count = 0
    with open(rpa_path, "rb") as f:
        parts = f.readline().split()
        magic = parts[0] if parts else b""
        if magic == b"RPA-3.0":
            offset = int(parts[1], 16)
            key = int(parts[2], 16)
        elif magic == b"RPA-2.0":
            offset = int(parts[1], 16)
            key = 0
        else:
            raise ValueError("Not an RPA-2/3 archive: %r" % magic)
        f.seek(offset)
        index = _load_index(f.read())

        for raw_name, entry in index.items():
            name = _text(raw_name)
            if scripts_only and not name.lower().endswith(SCRIPT_EXT):
                continue
            rel = _safe_rel(name)
            if rel is None:
                sys.stderr.write("skip %s: путь вне папки распаковки\n" % name)
                continue
            # entry = list of (offset, length[, prefix])
            e = entry[0]
            off = e[0] ^ key
            length = e[1] ^ key
            prefix = e[2] if len(e) > 2 else b""
            if isinstance(prefix, str):
                prefix = prefix.encode("latin-1")
            f.seek(off)
            data = prefix + f.read(length - len(prefix))
            dest = os.path.join(outdir, rel)
            try:
                os.makedirs(_long(os.path.dirname(dest)), exist_ok=True)
                with open(_long(dest), "wb") as out:
                    out.write(data)
                count += 1
            except OSError as e:
                sys.stderr.write("skip %s: %s\n" % (name, e))
    return count
