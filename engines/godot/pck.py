"""Чтение .pck Godot (форматы 1 — Godot 3, 2 — Godot 4.0–4.4, 3 — Godot 4.5+) без самого Godot.

Отдельный .pck рядом с .exe или пакет, вшитый в конец .exe (трейлер «размер + GDPC»).
Только каталог и чтение файлов; зашифрованный каталог — PckError.
"""

import os
import struct

MAGIC = b"GDPC"
FLAG_ENCRYPTED_DIR = 1
FLAG_REL_FILEBASE = 2
FLAG_FILE_REMOVAL = 2  # флаг записи каталога (Godot 4.4+), не пакета


class PckError(Exception):
    pass


class Pck:
    def __init__(self, path):
        self.path = path
        self.files = {}  # «res://…» -> (абсолютное смещение, размер, флаги)
        with open(path, "rb") as f:
            start = self._find_start(f)
            f.seek(start)
            magic, fmt, major, minor, patch = struct.unpack("<4sIIII", f.read(20))
            if magic != MAGIC:
                raise PckError(f"не .pck Godot: {path}")
            self.format, self.version = fmt, (major, minor, patch)
            flags, base = 0, 0
            if fmt >= 2:
                flags, base = struct.unpack("<IQ", f.read(12))
            if fmt >= 3:
                (dir_ofs,) = struct.unpack("<Q", f.read(8))
            f.read(16 * 4)
            if flags & FLAG_ENCRYPTED_DIR:
                raise PckError("каталог .pck зашифрован (ключ внутри .exe)")
            if fmt >= 3:
                f.seek(start + dir_ofs)
            if flags & FLAG_REL_FILEBASE:
                base += start
            (n,) = struct.unpack("<I", f.read(4))
            for _ in range(n):
                (ln,) = struct.unpack("<I", f.read(4))
                name = f.read(ln).rstrip(b"\0").decode("utf-8", "replace")
                ofs, size = struct.unpack("<QQ", f.read(16))
                f.read(16)  # md5
                fl = struct.unpack("<I", f.read(4))[0] if fmt >= 2 else 0
                if fl & FLAG_FILE_REMOVAL:
                    continue  # патч-пакет: запись «файл удалён», данных нет
                if not name.startswith("res://"):
                    name = "res://" + name
                self.files[name] = (
                    (base + ofs) if fmt >= 2 else (start + ofs),
                    size,
                    fl,
                )

    @staticmethod
    def _find_start(f):
        head = f.read(4)
        if head == MAGIC:
            return 0
        # вшитый в .exe: последние 12 байт — <размер пакета:uint64><GDPC>
        f.seek(-12, os.SEEK_END)
        size, magic = struct.unpack("<Q4s", f.read(12))
        if magic != MAGIC:
            raise PckError("в файле нет пакета Godot")
        end = f.tell() - 12
        return end - size

    def read(self, name):
        ofs, size, fl = self.files[name]
        if fl & 1:
            raise PckError(f"файл зашифрован: {name}")
        with open(self.path, "rb") as f:
            f.seek(ofs)
            return f.read(size)

    def text(self, name):
        return self.read(name).decode("utf-8", "replace")


def find_pack(folder):
    """(путь к .pck или .exe со вшитым пакетом) в папке игры или None."""
    if os.path.isfile(folder):
        folder = os.path.dirname(folder)
    pcks = [
        os.path.join(folder, f)
        for f in os.listdir(folder)
        if f.lower().endswith(".pck")
    ]
    if pcks:
        return max(pcks, key=os.path.getsize)
    for f in os.listdir(folder):
        p = os.path.join(folder, f)
        if f.lower().endswith(".exe") and os.path.getsize(p) > 1_000_000:
            try:
                Pck(p)
                return p
            except (PckError, OSError, struct.error):
                continue
    return None
