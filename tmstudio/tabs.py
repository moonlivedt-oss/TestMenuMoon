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


# ============================================================ вкладка: Обзор
class OverviewTab(QWidget):
    """Заголовок/статус/пути игры + кнопки действий над ней."""

    def __init__(
        self,
        on_dirty,
        on_save,
        on_save_deploy,
        on_validate,
        on_verify,
        on_open,
        on_uninstall,
        on_launch,
        default_accent=ACCENT,
    ):
        super().__init__()
        self._default_accent = default_accent
        self._on_dirty = on_dirty
        g = QGridLayout(self)
        g.setContentsMargins(16, 16, 16, 16)
        g.setVerticalSpacing(10)
        r = 0
        g.addWidget(QLabel("Название в меню"), r, 0)
        self.ed_title = QLineEdit()
        self.ed_title.textEdited.connect(on_dirty)
        g.addWidget(self.ed_title, r, 1)
        r += 1
        g.addWidget(QLabel("Заметка"), r, 0)
        self.ed_status = QLineEdit()
        self.ed_status.textEdited.connect(on_dirty)
        g.addWidget(self.ed_status, r, 1)
        r += 1
        g.addWidget(QLabel("Цвет меню"), r, 0)
        arow = QHBoxLayout()
        self.ed_accent = QLineEdit()
        self.ed_accent.setPlaceholderText(f"как у всех игр ({default_accent})")
        self.ed_accent.textEdited.connect(on_dirty)
        self.ed_accent.textEdited.connect(lambda: self._update_swatch())
        self.sw_accent = QPushButton()
        self.sw_accent.setFixedSize(22, 22)
        self.sw_accent.setCursor(Qt.CursorShape.PointingHandCursor)
        self.sw_accent.setToolTip("Выбрать цвет меню")
        self.sw_accent.clicked.connect(self._pick_color)
        arow.addWidget(self.ed_accent, 1)
        arow.addWidget(self.sw_accent)
        g.addLayout(arow, r, 1)
        r += 1
        g.addWidget(QLabel("Папка игры"), r, 0)
        self.lb_root = QLabel("—", objectName="dim")
        self.lb_root.setWordWrap(True)
        g.addWidget(self.lb_root, r, 1)
        r += 1
        g.addWidget(QLabel("Запуск"), r, 0)
        self.lb_launcher = QLabel("—", objectName="dim")
        self.lb_launcher.setWordWrap(True)
        g.addWidget(self.lb_launcher, r, 1)
        r += 1
        g.addWidget(QLabel("Меню в игре"), r, 0)
        self.lb_installed = QLabel("—", objectName="accent")
        g.addWidget(self.lb_installed, r, 1)
        r += 1
        g.addWidget(QLabel("Движок"), r, 0)
        self.lb_engine = QLabel("—", objectName="dim")
        g.addWidget(self.lb_engine, r, 1)
        r += 1
        g.addWidget(hline(), r, 0, 1, 2)
        r += 1

        row = QHBoxLayout()
        # одна главная кнопка; «Сохранить» без установки — Ctrl+S (окно), отдельной кнопки нет
        b_save = ibtn("Применить в игре", "upload", "Сохранить правки и поставить или обновить меню в игре")
        b_save.setObjectName("primary")
        self.b_save_deploy = b_save
        b_save.clicked.connect(on_save_deploy)
        b_run = ibtn("Запустить", "rocket", "Запустить игру, чтобы посмотреть меню")
        self.b_run = b_run
        b_run.clicked.connect(on_launch)
        # одна проверка: данные меню без запуска игры, у Ren'Py ещё и lint самой игры
        self._on_validate, self._on_verify = on_validate, on_verify
        b_chk = ibtn("Проверить", "checklist")
        b_chk.clicked.connect(self._check)
        self.b_chk = b_chk
        self._renpy = True
        b_open = ibtn("Открыть папку", "load", "Открыть папку игры в проводнике")
        b_open.clicked.connect(on_open)
        b_uni = ibtn("Удалить меню", "trash", "Убрать меню из игры (файлы самой игры не трогаются)")
        b_uni.setObjectName("danger")
        b_uni.clicked.connect(on_uninstall)
        for b in (b_save, b_run, b_chk, b_open):
            row.addWidget(b)
        row.addStretch(1)
        row.addWidget(b_uni)
        g.addLayout(row, r, 0, 1, 2)
        r += 1
        g.setRowStretch(r, 1)
        self.run_buttons = [b_save, b_chk, b_uni]
        self.set_renpy(True)

    def _check(self):
        self._on_validate()
        if self._renpy:
            self._on_verify()

    def set_busy(self, busy):
        self._busy = busy
        for b in self.run_buttons:
            b.setEnabled(not busy)

    def set_renpy(self, renpy):
        """Lint — только для Ren'Py: у Twine/RPG Maker verify падал с ошибкой."""
        self._renpy = renpy
        self.b_chk.setToolTip(
            "Проверить данные меню и прогнать проверку самой игры (lint Ren'Py)"
            if renpy
            else "Проверить данные меню: код выдачи, повторы, группы"
        )

    def load(
        self, title, status, root, launcher_text, installed_text, engine_text, accent=""
    ):
        self.ed_title.setText(title)
        self.ed_status.setText(status)
        self.ed_accent.setText(accent)
        self._update_swatch()
        self.lb_root.setText(root)
        self.lb_launcher.setText(launcher_text)
        self.lb_installed.setText(installed_text)
        self.lb_engine.setText(engine_text)

    def read(self):
        """(title, status, accent) — дефолт заголовка как раньше; пустой акцент = наследовать."""
        return (
            self.ed_title.text().strip() or "TEST MENU",
            self.ed_status.text().strip(),
            self.ed_accent.text().strip(),
        )

    def _update_swatch(self):
        col = self.ed_accent.text().strip() or self._default_accent
        if not QColor(col).isValid():
            col = "transparent"
        self.sw_accent.setStyleSheet(
            f"background:{col}; border:1px solid #23262f; border-radius:5px;"
        )

    def _pick_color(self):
        cur = self.ed_accent.text().strip() or self._default_accent
        col = QColorDialog.getColor(QColor(cur), self, "Акцент игры")
        if col.isValid():
            self.ed_accent.setText(col.name())  # #rrggbb
            self._update_swatch()
            self._on_dirty()

    def set_installed(self, text):
        self.lb_installed.setText(text)


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


