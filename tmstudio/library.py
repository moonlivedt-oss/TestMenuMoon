"""Библиотека игр: указать папку — студия сама находит игры, их движок и состояние меню.

Отмеченные строки можно разом поставить/обновить, снять или добавить в студию (манифест).
Логика поиска и установки — tmkit/library.py (её же зовёт `tm.py library`).
"""

import os

from PyQt6.QtCore import Qt, QSettings
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from tmkit import library
from tmstudio.theme import DIM, ENGINE_BADGE, GOOD, MUTE, WARN, ibtn
from tmstudio.tokens import ENGINE

STATUS_TEXT = {"ok": "свежее", "stale": "устарело", "none": "нет", "?": "не понять"}
STATUS_COLOR = {"ok": GOOD, "stale": WARN, "none": MUTE, "?": DIM}
COLS = ("", "Игра", "Движок", "Меню", "В моих играх", "Папка")


class LibraryDialog(QDialog):
    """games — манифест студии (dict); on_add(root, title) -> индекс; on_changed() — перерисовать."""

    def __init__(self, parent, games, on_add, on_changed):
        super().__init__(parent)
        self.setWindowTitle("Библиотека игр")
        self.resize(980, 600)
        self.games, self.on_add, self.on_changed = games, on_add, on_changed
        self.found = []
        self.settings = QSettings("TestMenuMoon", "Studio")

        v = QVBoxLayout(self)
        top = QHBoxLayout()
        self.folder = QLineEdit(self.settings.value("library_dir", "") or "")
        self.folder.setPlaceholderText("папка с играми, например D:/Games")
        self.folder.returnPressed.connect(self.scan)
        b_pick = QPushButton("Выбрать…")
        b_pick.clicked.connect(self._pick)
        b_scan = ibtn("Найти игры", "m_search", "Просмотреть папку на 2 уровня вниз")
        b_scan.setObjectName("primary")
        b_scan.clicked.connect(self.scan)
        top.addWidget(self.folder, 1)
        top.addWidget(b_pick)
        top.addWidget(b_scan)
        v.addLayout(top)

        # фильтр: все / где нужно обновить / где меню нет
        seg = QHBoxLayout()
        seg.setSpacing(6)
        self.seg = {}
        for key, text in (("all", "Все"), ("stale", "Нужно обновить"), ("none", "Без меню")):
            b = QPushButton(text)
            b.setObjectName("chip")
            b.setCheckable(True)
            b.setChecked(key == "all")
            b.clicked.connect(lambda _=False, k=key: self._set_view(k))
            seg.addWidget(b)
            self.seg[key] = b
        seg.addStretch(1)
        v.addLayout(seg)
        self.view = "all"

        self.table = QTableWidget(0, len(COLS))
        self.table.setHorizontalHeaderLabels(COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setAlternatingRowColors(True)
        h = self.table.horizontalHeader()
        h.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        h.setSectionResizeMode(5, QHeaderView.ResizeMode.Stretch)
        self.table.cellDoubleClicked.connect(self._toggle_row)
        v.addWidget(self.table, 1)
        from tmstudio.theme import ICON_DIR
        from tmstudio.widgets import EmptyGuide

        # пока папку не просматривали — подсказка вместо пустой таблицы
        self.guide = EmptyGuide(
            os.path.join(ICON_DIR, "m_search.png"),
            "Все игры из одной папки",
            "Студия найдёт игры на 2 уровня вниз, определит движок и покажет, где меню нет или оно "
            "устарело. Ставить и обновлять можно пачкой.",
            [
                ("Укажи папку", "где лежат игры, например D:/Games — поле сверху или «Выбрать…»"),
                ("Найти игры", "студия покажет движок, состояние меню и есть ли игра в твоём списке"),
                ("Отметь и поставь", "«Отметить без меню и устаревшие» → «Поставить / обновить»"),
            ],
            buttons=[("Выбрать папку", self._pick)] + ([("Найти игры", self.scan)] if self.folder.text() else []),
        )
        v.addWidget(self.guide, 1)
        self.table.hide()

        self.info = QLabel("", objectName="dim")
        self.info.setWordWrap(True)
        v.addWidget(self.info)

        bar = QHBoxLayout()
        for text, icon, tip, fn in (
            (
                "Отметить все",
                "checklist",
                "Отметить все игры",
                lambda: self._mark(lambda g: True),
            ),
            (
                "Отметить без меню и устаревшие",
                "warn",
                "Отметить, где меню нет или оно старое",
                lambda: self._mark(lambda g: g.status in ("none", "stale")),
            ),
            ("Снять отметки", "close", None, lambda: self._mark(lambda g: False)),
        ):
            b = ibtn(text, icon, tip)
            b.clicked.connect(fn)
            bar.addWidget(b)
        bar.addStretch(1)
        b_inst = ibtn(
            "Поставить / обновить",
            "download",
            "Поставить меню в отмеченные игры (или обновить)",
        )
        b_inst.setObjectName("primary")
        b_inst.clicked.connect(lambda: self._apply(library.install, "установка"))
        b_rem = ibtn("Снять", "trash", "Снять меню из отмеченных игр")
        b_rem.setObjectName("danger")
        b_rem.clicked.connect(lambda: self._apply(library.remove, "снятие"))
        b_add = ibtn(
            "В мои игры", "plus", "Добавить отмеченные игры в список студии"
        )
        b_add.clicked.connect(self._add_to_studio)
        for b in (b_inst, b_rem, b_add):
            bar.addWidget(b)
        v.addLayout(bar)
        if self.folder.text():
            self.info.setText("Нажми «Найти игры», чтобы просмотреть папку.")

    # ---------------------------------------------------------------- поиск
    def _pick(self):
        d = QFileDialog.getExistingDirectory(self, "Папка с играми", self.folder.text())
        if d:
            self.folder.setText(d)
            self.scan()

    def scan(self):
        d = self.folder.text().strip()
        if not d or not os.path.isdir(d):
            self.info.setText("Нет такой папки.")
            return
        self.settings.setValue("library_dir", d)
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.found = library.find_games(d, games=self.games)
        finally:
            QApplication.restoreOverrideCursor()
        self._fill()
        n = {s: sum(1 for g in self.found if g.status == s) for s in STATUS_TEXT}
        self.seg["all"].setText(f"Все  {len(self.found)}")
        self.seg["stale"].setText(f"Нужно обновить  {n['stale']}")
        self.seg["none"].setText(f"Без меню  {n['none']}")
        self._set_view(self.view)
        self.info.setText(
            f"Найдено игр: {len(self.found)}. Меню актуальное: {n['ok']}, устарело: {n['stale']}, "
            f"нет: {n['none']}. Двойной щелчок по строке — отметить."
        )

    def _fill(self):
        self.guide.hide()
        self.table.show()
        self.table.setRowCount(len(self.found))
        for r, g in enumerate(self.found):
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
            chk.setCheckState(Qt.CheckState.Unchecked)
            self.table.setItem(r, 0, chk)
            self._row(r, g)

    def _set_view(self, key):
        self.view = key
        for k, b in self.seg.items():
            b.setChecked(k == key)
        for r, g in enumerate(self.found):
            self.table.setRowHidden(r, key != "all" and g.status != key)

    def _row(self, r, g):
        cells = (
            g.name,
            ENGINE_BADGE.get(g.engine.key, g.engine.title),
            STATUS_TEXT.get(g.status, g.status),
            "да" if g.index is not None else "",
            g.folder,
        )
        for c, text in enumerate(cells, start=1):
            it = QTableWidgetItem(text)
            if c == 2 and g.engine.key in ENGINE:
                it.setForeground(QColor(ENGINE[g.engine.key][1]))
            if c == 3:
                it.setForeground(QColor(STATUS_COLOR.get(g.status, DIM)))
            if c == 5:
                it.setForeground(QColor(DIM))
            self.table.setItem(r, c, it)

    def _toggle_row(self, r, _c):
        it = self.table.item(r, 0)
        on = it.checkState() == Qt.CheckState.Checked
        it.setCheckState(Qt.CheckState.Unchecked if on else Qt.CheckState.Checked)

    def _mark(self, pred):
        for r, g in enumerate(self.found):
            st = Qt.CheckState.Checked if pred(g) else Qt.CheckState.Unchecked
            self.table.item(r, 0).setCheckState(st)

    def _checked(self):
        rows = [
            r
            for r in range(self.table.rowCount())
            if self.table.item(r, 0).checkState() == Qt.CheckState.Checked
        ]
        if not rows:
            self.info.setText(
                "Ничего не отмечено: отметь игры галочкой или кнопками слева."
            )
        return rows

    # ---------------------------------------------------------------- действия
    def _apply(self, fn, verb):
        rows = self._checked()
        if not rows:
            return
        ok, errors = 0, []
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for r in rows:
                g = self.found[r]
                try:
                    fn(g)
                    ok += 1
                except Exception as e:  # одна игра не обрывает остальные
                    errors.append(f"{g.name}: {e}")
                library.refresh(g, self.games)
                self._row(r, g)
                QApplication.processEvents()
        finally:
            QApplication.restoreOverrideCursor()
        text = f"{verb}: готово {ok} из {len(rows)}."
        if errors:
            text += " Ошибки: " + " | ".join(errors[:4])
        self.info.setText(text)
        self.on_changed()

    def _add_to_studio(self):
        rows = self._checked()
        if not rows:
            return
        added = 0
        for r in rows:
            g = self.found[r]
            if g.index is not None:
                continue
            g.index = self.on_add(g.target, g.name)
            self._row(r, g)
            added += 1
        self.info.setText(
            f"Добавлено в студию: {added} (уже были: {len(rows) - added})."
        )
        self.on_changed()
