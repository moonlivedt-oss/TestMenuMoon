"""Вкладки карточки игры: «Основное», таблицы «Статы» / «Выдача», «Поиск переменных».

Каждая вкладка — свой QWidget; окно (tmstudio.window.Studio) связывает их колбэками.
"""


from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QColor, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QPlainTextEdit,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QAbstractItemView,
    QColorDialog,
)

from tmkit import manifest  # чтение/запись games_data.py
from tmkit import analysis  # разбор строк кандидатов -> пары для таблицы статов

from tmstudio.theme import ACCENT, hline, ibtn, mascot_box
from tmstudio.widgets import AccentPicker


# ============================================================ вкладка: Основное
class OverviewTab(QWidget):
    """Название, заметка, цвет меню и сведения об игре. Кнопки действий — в шапке игры (окно)."""

    def __init__(self, on_dirty, default_accent=ACCENT):
        super().__init__()
        self._default_accent = default_accent
        self._on_dirty = on_dirty
        g = QGridLayout(self)
        g.setContentsMargins(20, 18, 20, 18)
        g.setHorizontalSpacing(16)
        g.setVerticalSpacing(12)
        r = 0
        g.addWidget(QLabel("Название в меню", objectName="dim"), r, 0)
        self.ed_title = QLineEdit()
        self.ed_title.setPlaceholderText("как будет подписано окно меню в игре")
        self.ed_title.textEdited.connect(on_dirty)
        g.addWidget(self.ed_title, r, 1)
        r += 1
        g.addWidget(QLabel("Заметка", objectName="dim"), r, 0)
        self.ed_status = QLineEdit()
        self.ed_status.setPlaceholderText("для себя: что проверено, что сломано")
        self.ed_status.textEdited.connect(on_dirty)
        g.addWidget(self.ed_status, r, 1)
        r += 1
        g.addWidget(QLabel("Цвет меню", objectName="dim"), r, 0)
        self.accent = AccentPicker(default_accent, self._pick_color)
        self.accent.changed.connect(on_dirty)
        g.addWidget(self.accent, r, 1)
        r += 1
        g.addWidget(hline(), r, 0, 1, 2)
        r += 1
        self.info = {}
        for key, label in (
            ("installed", "Меню в игре"),
            ("engine", "Движок"),
            ("root", "Папка игры"),
            ("launcher", "Запуск"),
        ):
            g.addWidget(QLabel(label, objectName="dim"), r, 0)
            lb = QLabel("—", objectName="accent" if key == "installed" else "")
            lb.setWordWrap(True)
            lb.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            g.addWidget(lb, r, 1)
            self.info[key] = lb
            r += 1
        g.setColumnStretch(1, 1)
        g.setRowStretch(r, 1)

    def load(self, title, status, root, launcher_text, installed_text, engine_text, accent=""):
        self.ed_title.setText(title)
        self.ed_status.setText(status)
        self.accent.set_value(accent)
        self.info["root"].setText(root)
        self.info["launcher"].setText(launcher_text)
        self.info["installed"].setText(installed_text)
        self.info["engine"].setText(engine_text)

    def read(self):
        """(title, status, accent) — дефолт заголовка как раньше; пустой цвет = общий."""
        return (
            self.ed_title.text().strip() or "TEST MENU",
            self.ed_status.text().strip(),
            self.accent.value(),
        )

    def _pick_color(self):
        cur = self.accent.value() or self._default_accent
        col = QColorDialog.getColor(QColor(cur), self, "Цвет меню")
        if col.isValid():
            self.accent.set_value(col.name(), user=True)  # #rrggbb

    def set_installed(self, text):
        self.info["installed"].setText(text)
# ================================================ вкладка: таблица (статы/действия)
class TableTab(QWidget):
    """Редактор пар «метка / значение» (одинаков для Статов и Выдачи)."""

    def __init__(self, headers, section_label, on_dirty):
        super().__init__()
        self.on_dirty = on_dirty
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 14, 14, 14)

        self.ncols = len(headers)
        self.table = QTableWidget(0, self.ncols)
        self.table.setHorizontalHeaderLabels(headers)
        self.table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.ResizeMode.Interactive
        )
        self.table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeMode.Stretch
        )
        self.table.setColumnWidth(0, 240)
        for c in range(2, self.ncols):  # min / max — узкие колонки справа
            self.table.horizontalHeader().setSectionResizeMode(
                c, QHeaderView.ResizeMode.Interactive
            )
            self.table.setColumnWidth(c, 130)
        self.table.verticalHeader().setDefaultSectionSize(30)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.table.setAlternatingRowColors(True)
        self.table.itemChanged.connect(on_dirty)
        # только когда фокус на самой таблице — в редакторе ячейки Del/Ctrl+D остаются текстовыми
        for seq, fn in (
            (QKeySequence(Qt.Key.Key_Delete), self._row_del),
            (QKeySequence("Ctrl+D"), self._row_dup),
        ):
            sc = QShortcut(seq, self.table)
            sc.setContext(Qt.ShortcutContext.WidgetShortcut)
            sc.activated.connect(fn)

        v.addLayout(self._toolbar(section_label))
        v.addWidget(self.table)

    def _toolbar(self, section_label):
        row = QHBoxLayout()
        b_add = ibtn("строка", "plus", "Добавить строку под выделенной")
        b_add.clicked.connect(lambda: self._row_add())
        b_sec = ibtn("секция", "flag", "Заголовок секции (пустой путь)")
        b_sec.clicked.connect(lambda: self._row_add(section=True))
        b_del = ibtn("удалить", "trash", "Удалить выделенные строки (Del)")
        b_del.clicked.connect(self._row_del)
        b_dup = ibtn("дубль", "clipboard", "Дублировать строку (Ctrl+D)")
        b_dup.clicked.connect(self._row_dup)
        b_up = QPushButton("↑")
        b_up.clicked.connect(lambda: self._row_move(-1))
        b_dn = QPushButton("↓")
        b_dn.clicked.connect(lambda: self._row_move(+1))
        for b in (b_add, b_sec, b_del, b_dup, b_up, b_dn):
            row.addWidget(b)
        row.addStretch(1)
        row.addWidget(QLabel(section_label, objectName="dim"))
        return row

    # ---- модель ----
    def fill(self, pairs):
        self.table.blockSignals(True)
        self.table.setRowCount(0)
        for row in pairs:
            r = self.table.rowCount()
            self.table.insertRow(r)
            cells = (tuple(row) + ("",) * self.ncols)[: self.ncols]
            for c, val in enumerate(cells):
                self.table.setItem(r, c, QTableWidgetItem(str(val)))
        self.table.blockSignals(False)

    def read(self):
        out = []
        for r in range(self.table.rowCount()):
            cells = []
            for c in range(self.ncols):
                it = self.table.item(r, c)
                t = it.text() if it else ""
                cells.append(t.strip() if c >= 2 else t)
            if not any(cells):
                continue
            out.append(manifest.trim_row(cells))
        return out

    # ---- правка строк ----
    def _row_add(self, section=False):
        r = self.table.currentRow()
        r = self.table.rowCount() if r < 0 else r + 1
        self.table.insertRow(r)
        self.table.setItem(r, 0, QTableWidgetItem("— секция —" if section else ""))
        for c in range(1, self.ncols):
            self.table.setItem(r, c, QTableWidgetItem(""))
        self.table.setCurrentCell(r, 0)
        self.on_dirty()

    def add_pairs(self, pairs):
        """Дописать пары в конец, пропуская уже имеющиеся значения. Возвращает число добавленных."""
        have = {row[1] for row in self.read()}
        added = 0
        self.table.blockSignals(True)
        for row in pairs:
            b = row[1]
            if b in have:
                continue
            have.add(b)
            r = self.table.rowCount()
            self.table.insertRow(r)
            cells = (tuple(row) + ("",) * self.ncols)[: self.ncols]
            for c, val in enumerate(cells):
                self.table.setItem(r, c, QTableWidgetItem(str(val)))
            added += 1
        self.table.blockSignals(False)
        if added:
            self.table.scrollToBottom()
            self.on_dirty()
        return added

    def _row_del(self):
        rows = sorted({ix.row() for ix in self.table.selectedIndexes()})
        if not rows and self.table.currentRow() >= 0:
            rows = [self.table.currentRow()]
        for r in reversed(rows):
            self.table.removeRow(r)
        if rows:
            self.on_dirty()

    def _row_dup(self):
        r = self.table.currentRow()
        if r < 0:
            return
        self.table.blockSignals(True)
        self.table.insertRow(r + 1)
        for c in range(self.ncols):
            it = self.table.item(r, c)
            self.table.setItem(r + 1, c, QTableWidgetItem(it.text() if it else ""))
        self.table.blockSignals(False)
        self.table.setCurrentCell(r + 1, max(0, self.table.currentColumn()))
        self.on_dirty()

    def _row_move(self, d):
        r = self.table.currentRow()
        nr = r + d
        if r < 0 or nr < 0 or nr >= self.table.rowCount():
            return
        self.table.blockSignals(True)
        for c in range(self.ncols):
            a = self.table.takeItem(r, c)
            b = self.table.takeItem(nr, c)
            self.table.setItem(r, c, b)
            self.table.setItem(nr, c, a)
        self.table.blockSignals(False)
        self.table.setCurrentCell(nr, self.table.currentColumn())
        self.on_dirty()


# ============================================================ вкладка: Кандидаты
class CandidatesTab(QWidget):
    """Кнопки распаковки/поиска кандидатов + просмотр файла кандидатов."""

    def __init__(
        self, hint_text, on_collect, on_curate, on_refresh, on_full, on_add_stats
    ):
        super().__init__()
        self._hint_renpy = hint_text
        self._text = ""
        self._on_add_stats = on_add_stats
        v = QVBoxLayout(self)
        v.setContentsMargins(14, 14, 14, 14)
        row = QHBoxLayout()
        self.b_col = ibtn("1. Распаковать игру", "puzzle")
        self.b_col.clicked.connect(on_collect)
        self.b_cur = ibtn("2. Найти переменные", "scanner")
        self.b_cur.clicked.connect(on_curate)
        b_ref = ibtn("Обновить", "back")
        b_ref.clicked.connect(on_refresh)
        self.b_full = ibtn("Всё сразу", "rocket")
        self.b_full.setObjectName("primary")
        self.b_full.setToolTip(
            "Распаковать игру, найти переменные, собрать и поставить меню (по очереди)"
        )
        self.b_full.clicked.connect(on_full)
        row.addWidget(self.b_col)
        row.addWidget(self.b_cur)
        row.addWidget(b_ref)
        row.addStretch(1)
        row.addWidget(self.b_full)
        v.addLayout(row)
        self.hint = QLabel(hint_text, objectName="dim")
        v.addWidget(self.hint)
        frow = QHBoxLayout()
        self.ed_filter = QLineEdit()
        self.ed_filter.setPlaceholderText("Фильтр строк (заголовки групп остаются)")
        self.ed_filter.setClearButtonEnabled(True)
        self.ed_filter.textChanged.connect(lambda _t: self._render())
        self.b_add = ibtn("В статы", "stats")
        self.b_add.setToolTip(
            "Добавить выделенные строки (или строку под курсором) в таблицу статов"
        )
        self.b_add.clicked.connect(self._add_selected)
        frow.addWidget(self.ed_filter, 1)
        frow.addWidget(self.b_add)
        v.addLayout(frow)
        self.view = QPlainTextEdit()
        self.view.setReadOnly(True)
        self.view.setFont(QFont("Consolas", 10))
        v.addWidget(self.view)
        self.empty = mascot_box("m_wait", "")
        self.empty.hide()
        v.addWidget(self.empty)
        v.addStretch(0)
        self.run_buttons = [self.b_col, self.b_cur, self.b_full]

    def set_mode(self, renpy, hint=None):
        """Ren'Py: полный пайплайн (распаковка+курирование). Иначе — один скан данных движка:
        прячем Ren'Py-only кнопки, «Найти кандидатов» становится «Сканировать данные»."""
        self.b_col.setVisible(renpy)
        self.b_full.setVisible(renpy)
        self.b_cur.setText("2. Найти переменные" if renpy else "Найти переменные")
        self.b_add.setVisible(
            renpy
        )  # таблица статов есть только у манифестных (Ren'Py) игр
        self.hint.setText(hint or self._hint_renpy)

    def set_busy(self, busy):
        for b in self.run_buttons:
            b.setEnabled(not busy)

    def set_text(self, s, empty=False):
        """empty=True: файла кандидатов нет — вместо пустого поля маскот с подсказкой."""
        self._text = "" if empty else s
        self.view.setVisible(not empty)
        self.empty.setVisible(empty)
        if empty:
            self.empty.label.setText(s)
        self._render()

    def _render(self):
        q = self.ed_filter.text().strip().lower()
        if not q:
            self.view.setPlainText(self._text)
            return
        keep = [
            ln
            for ln in self._text.splitlines()
            if ln.startswith("#") or q in ln.lower()
        ]
        self.view.setPlainText("\n".join(keep))

    def _add_selected(self):
        cur = self.view.textCursor()
        # у выделения QTextCursor разделитель строк — U+2029, не \n
        text = (
            cur.selectedText().replace("\u2029", "\n")
            if cur.hasSelection()
            else cur.block().text()
        )
        self._on_add_stats(analysis.parse_candidates(text))


