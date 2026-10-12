#!/usr/bin/env python3
"""Редактор сохранений: Ren'Py (сейвы и persistent), RPG Maker MV/MZ, Unity (PlayerPrefs и JSON), Godot.

Открывается из студии (кнопка «Сохранения…») или сам:  python tm.py saves [файл сейва]
Форматы и запись — tmkit/saves.py. Перед первой записью рядом с файлом остаётся <файл>.tm_bak.
"""

import os, sys

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QApplication,
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QComboBox,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QFileDialog,
    QMessageBox,
)

# запуск файлом (python tmstudio/save_editor.py) — корень проекта в sys.path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tmkit import saves, engines  # noqa: E402
from tmkit.saves import diff as sdiff  # noqa: E402
from tmstudio.tokens import TOK  # noqa: E402

TYPE_NAMES = {
    bool: "флаг",
    int: "целое",
    float: "дробное",
    str: "строка",
    bytes: "строка (py2)",
}
EDITED = QColor("#3a3320")


class SaveEditor(QDialog):
    def __init__(self, parent=None, game_root=None, engine_key=None, path=None):
        super().__init__(parent)
        self.setWindowTitle("Редактор сохранений")
        self.resize(980, 680)
        self.doc = None
        self.items = []
        self.dirty = {}  # строка таблицы -> новое значение
        self._filling = False

        v = QVBoxLayout(self)
        top = QHBoxLayout()
        self.game_lbl = QLabel("", objectName="dim")
        top.addWidget(self.game_lbl, 1)
        b_dir = QPushButton("Найти в папке игры…")
        b_dir.setToolTip(
            "Выбрать папку игры: движок определится сам, сейвы найдутся (в т.ч. в %APPDATA%, LocalLow, реестре)"
        )
        b_dir.clicked.connect(self._pick_game)
        b_file = QPushButton("Открыть файл…")
        b_file.clicked.connect(self._pick_file)
        top.addWidget(b_dir)
        top.addWidget(b_file)
        v.addLayout(top)

        self.combo = QComboBox()
        self.combo.currentIndexChanged.connect(self._open_current)
        v.addWidget(self.combo)

        self.filter = QLineEdit()
        self.filter.setPlaceholderText("фильтр по имени или значению…")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self._apply_filter)
        v.addWidget(self.filter)

        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["Имя", "Значение", "Тип"])
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(1, 260)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.itemChanged.connect(self._edited)
        v.addWidget(self.table, 1)

        bottom = QHBoxLayout()
        self.status = QLabel("", objectName="dim")
        self.status.setWordWrap(True)
        bottom.addWidget(self.status, 1)
        b_snap = QPushButton("Снимок")
        b_snap.setToolTip("Запомнить все значения этого сейва (снимок хранится и после закрытия студии)")
        b_snap.clicked.connect(self._snapshot)
        b_cmp = QPushButton("Сравнить со снимком")
        b_cmp.setToolTip("Перечитать сейв с диска и показать, что изменилось с момента снимка")
        b_cmp.clicked.connect(self._compare_snapshot)
        b_cmp_file = QPushButton("Сравнить с файлом…")
        b_cmp_file.setToolTip("Показать разницу между этим сейвом и другим файлом")
        b_cmp_file.clicked.connect(self._compare_file)
        for b in (b_snap, b_cmp, b_cmp_file):
            bottom.addWidget(b)
        b_undo = QPushButton("Отменить правки")
        b_undo.clicked.connect(self._open_current)
        self.b_save = QPushButton("Сохранить")
        self.b_save.setObjectName("primary")
        self.b_save.setToolTip(
            "Записать правки (Ctrl+S). Оригинал один раз копируется в .tm_bak"
        )
        self.b_save.clicked.connect(self._save)
        bottom.addWidget(b_undo)
        bottom.addWidget(self.b_save)
        v.addLayout(bottom)
        QShortcut(QKeySequence("Ctrl+S"), self, activated=self._save)

        if path:
            self._set_targets("Файл", [("файл", path)])
        elif game_root:
            self._load_game(game_root, engine_key)
        else:
            self.status.setText(
                "Выбери папку игры или файл сохранения. Закрой игру перед записью."
            )

    # ---------------------------------------------------------- где искать
    def _load_game(self, root, engine_key=None):
        if engine_key is None:
            eng = engines.detect_engine(root)
            engine_key = eng.key if eng else ""
        found = saves.find_saves(root, engine_key)
        title = (
            engines.REGISTRY[engine_key].title
            if engine_key in engines.REGISTRY
            else "?"
        )
        self._set_targets("%s: %s" % (title, root), found)
        if not found:
            hint = {
                "web": "У HTML5-игр сейвы в localStorage браузера — их правит меню в игре.",
                "twine": "У Twine сейвы в localStorage браузера — правь переменные меню в игре.",
            }.get(engine_key, "")
            self.status.setText(
                "Сохранения не найдены. "
                + (hint or "Открой файл вручную («Открыть файл…»).")
            )

    def _set_targets(self, label, targets):
        self.game_lbl.setText(label)
        self.targets = targets
        self.combo.blockSignals(True)
        self.combo.clear()
        for lab, t in targets:
            if isinstance(t, tuple):
                self.combo.addItem("%s  %s / %s" % (lab, t[1], t[2]))
            else:
                try:
                    mt = os.path.getmtime(t)
                    import time

                    when = time.strftime("%d.%m.%Y %H:%M", time.localtime(mt))
                except OSError:
                    when = ""
                self.combo.addItem(
                    "%s  |  %s  |  %s" % (os.path.basename(t), lab, when)
                )
        self.combo.blockSignals(False)
        if targets:
            self.combo.setCurrentIndex(0)
            self._open_current()

    def _pick_game(self):
        d = QFileDialog.getExistingDirectory(self, "Папка игры")
        if d:
            self._load_game(d)

    def _pick_file(self):
        p, _f = QFileDialog.getOpenFileName(
            self,
            "Файл сохранения",
            "",
            "Сохранения (*.save *.rpgsave *.rmmzsave *.json *.sav *.dat *.cfg *.es3 *.txt persistent);;Все файлы (*)",
        )
        if p:
            self._set_targets("Файл", [("файл", p)])

    # ---------------------------------------------------------- открыть и показать
    def _open_current(self):
        i = self.combo.currentIndex()
        if i < 0 or i >= len(self.targets):
            return
        target = self.targets[i][1]
        try:
            self.doc = saves.open_any(target)
        except Exception as e:
            self.doc = None
            self.items = []
            self.table.setRowCount(0)
            self.status.setText("Не открыть: %s" % e)
            return
        self.items = self.doc.items()
        self.dirty = {}
        self._fill()
        self.status.setText(
            "%s: %d значений. Двойной щелчок по значению — правка; потом «Сохранить»."
            % (self.doc.title, len(self.items))
        )

    def _fill(self):
        self._filling = True
        self.table.setRowCount(len(self.items))
        for r, it in enumerate(self.items):
            a = QTableWidgetItem(it.label)
            a.setFlags(a.flags() & ~Qt.ItemFlag.ItemIsEditable)
            val = (
                it.value.decode("utf-8", "replace")
                if isinstance(it.value, bytes)
                else it.value
            )
            b = QTableWidgetItem(
                "true" if val is True else "false" if val is False else str(val)
            )
            c = QTableWidgetItem(
                TYPE_NAMES.get(type(it.value), type(it.value).__name__)
            )
            c.setFlags(c.flags() & ~Qt.ItemFlag.ItemIsEditable)
            for col, x in enumerate((a, b, c)):
                self.table.setItem(r, col, x)
        self._filling = False
        self._apply_filter()

    def _apply_filter(self):
        q = self.filter.text().strip().lower()
        for r in range(self.table.rowCount()):
            t = (
                self.table.item(r, 0).text() + " " + self.table.item(r, 1).text()
            ).lower()
            self.table.setRowHidden(r, bool(q) and q not in t)

    def _edited(self, item):
        if self._filling or item.column() != 1:
            return
        it = self.items[item.row()]
        try:
            new = saves.coerce(it.value, item.text())
        except ValueError as e:
            self.status.setText("«%s»: %s" % (it.label, e))
            self._filling = True
            item.setText(str(self.dirty.get(item.row(), it.value)))
            self._filling = False
            return
        self.dirty[item.row()] = new
        for col in range(3):
            self.table.item(item.row(), col).setBackground(EDITED)
        self.status.setText(
            "Изменено значений: %d — «Сохранить», чтобы записать." % len(self.dirty)
        )

    # ---------------------------------------------------------- снимки и сравнение
    def _target(self):
        i = self.combo.currentIndex()
        return self.targets[i][1] if 0 <= i < len(getattr(self, "targets", [])) else None

    def _snapshot(self):
        if not self.doc:
            self.status.setText("Сначала открой сейв.")
            return
        snap = sdiff.snapshot(self.doc)
        sdiff.save_snap(self._target(), snap)
        self.status.setText(
            "Снимок: %d значений. Поиграй, сохрани игру в этот же слот и нажми «Сравнить со снимком»." % len(snap)
        )

    def _compare_snapshot(self):
        target = self._target()
        old = sdiff.load_snap(target) if target is not None else None
        if old is None:
            self.status.setText("У этого сейва ещё нет снимка — нажми «Снимок».")
            return
        try:
            new = sdiff.snapshot(saves.open_any(target))
        except Exception as e:
            self.status.setText("Не открыть: %s" % e)
            return
        DiffDialog(self, "Снимок -> сейв сейчас", sdiff.diff(old, new)).exec()

    def _compare_file(self):
        if not self.doc:
            self.status.setText("Сначала открой сейв.")
            return
        p, _f = QFileDialog.getOpenFileName(self, "С каким сейвом сравнить", os.path.dirname(str(self._target() or "")))
        if not p:
            return
        try:
            other = sdiff.snapshot(saves.open_save(p))
        except Exception as e:
            self.status.setText("Не открыть: %s" % e)
            return
        title = "%s -> %s" % (os.path.basename(str(self._target())), os.path.basename(p))
        DiffDialog(self, title, sdiff.diff(sdiff.snapshot(self.doc), other)).exec()

    def _save(self):
        if not self.doc or not self.dirty:
            self.status.setText("Нечего сохранять.")
            return
        try:
            for r, val in self.dirty.items():
                self.doc.set(self.items[r].path, val)
            self.doc.save()
        except Exception as e:
            QMessageBox.critical(self, "Не записано", "Сохранение не записано:\n%s" % e)
            return
        n = len(self.dirty)
        note = getattr(self.doc, "note", "")
        self._open_current()
        self.status.setText(
            "Записано правок: %d. %s Перезагрузи сохранение в игре."
            % (n, (note + ".") if note else "")
        )


class DiffDialog(QDialog):
    """Таблица изменений: поле, было, стало (новые и пропавшие значения — отдельно)."""

    KIND = {"changed": "изменилось", "added": "появилось", "removed": "пропало"}

    def __init__(self, parent, title, changes):
        super().__init__(parent)
        self.setWindowTitle("Что изменилось: " + title)
        self.resize(900, 560)
        v = QVBoxLayout(self)
        n = {k: sum(1 for c in changes if c.kind == k) for k in self.KIND}
        v.addWidget(QLabel(
            "Изменилось: %d, появилось: %d, пропало: %d." % (n["changed"], n["added"], n["removed"])
            if changes else "Различий нет.",
            objectName="dim",
        ))
        flt = QLineEdit()
        flt.setPlaceholderText("фильтр по имени…")
        flt.setClearButtonEnabled(True)
        v.addWidget(flt)
        t = QTableWidget(len(changes), 4)
        t.setHorizontalHeaderLabels(["Имя", "Было", "Стало", ""])
        t.verticalHeader().setVisible(False)
        t.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        hh = t.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for c in (1, 2, 3):
            hh.setSectionResizeMode(c, QHeaderView.ResizeMode.ResizeToContents)
        for r, ch in enumerate(changes):
            for col, text in enumerate((ch.label, sdiff.text(ch.before), sdiff.text(ch.after), self.KIND[ch.kind])):
                it = QTableWidgetItem(text)
                if ch.kind == "changed" and col == 2:
                    it.setForeground(QColor(TOK["ok"]))
                elif ch.kind != "changed":
                    it.setForeground(QColor(TOK["text_hint"]))
                t.setItem(r, col, it)
        v.addWidget(t, 1)

        def apply(q):
            q = q.strip().lower()
            for r in range(t.rowCount()):
                t.setRowHidden(r, bool(q) and q not in t.item(r, 0).text().lower())

        flt.textChanged.connect(apply)
        b = QPushButton("Закрыть")
        b.clicked.connect(self.accept)
        v.addWidget(b, 0, Qt.AlignmentFlag.AlignRight)


def main(path=None):
    app = QApplication(sys.argv)
    from tmstudio.theme import QSS

    app.setStyleSheet(QSS)
    w = SaveEditor(path=path)
    w.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1] if len(sys.argv) > 1 else None))
