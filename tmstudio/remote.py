"""Пульт: управление запущенной игрой из студии (второй монитор, меню не закрывает игру).

Студия поднимает мост tmkit/bridge.py (127.0.0.1:47820); игра подключается, когда в её меню
включён «Пульт в студии» (веб-меню — вкладка «Игра», Ren'Py — «Настройки»). Здесь — живые
значения игры: правка двойным щелчком, заморозка галочкой, темп и шаг кадра.
"""

import os

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QColor
from PyQt6.QtWidgets import (
    QWidget,
    QAbstractItemView,
    QComboBox,
    QDialog,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from tmkit import bridge as tmbridge
from tmstudio.theme import DIM, GOOD, MUTE

SPEEDS = ((0, "пауза"), (0.25, "×0.25"), (0.5, "×0.5"), (1, "×1"), (2, "×2"), (3, "×3"), (5, "×5"))
_BRIDGE = None


def bridge():
    """Один мост на процесс студии (окно можно закрывать и открывать — игры остаются на связи)."""
    global _BRIDGE
    if _BRIDGE is None:
        _BRIDGE = tmbridge.Bridge()
        _BRIDGE.start()
    return _BRIDGE


def _text(v):
    return "true" if v is True else "false" if v is False else str(v)


class RemoteDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Пульт: игра на связи со студией")
        self.resize(820, 680)
        self.setWindowFlag(Qt.WindowType.WindowMinMaxButtonsHint, True)
        self.br = bridge()
        self.cid = None
        self.keys = []  # ключи строк таблицы по порядку
        self._filling = False

        v = QVBoxLayout(self)
        self.info = QLabel("", objectName="dim")
        self.info.setWordWrap(True)
        v.addWidget(self.info)
        # рабочая часть (игра на связи) и подсказка, пока связи нет
        self.work = QWidget()
        wv = QVBoxLayout(self.work)
        wv.setContentsMargins(0, 0, 0, 0)
        self.combo = QComboBox()
        self.combo.currentIndexChanged.connect(self._pick)
        wv.addWidget(self.combo)

        self.speed_row = QHBoxLayout()
        self.speed_btns = []
        for k, label in SPEEDS:
            b = QPushButton(label)
            b.clicked.connect(lambda _c=False, k=k: self._send("speed", v=k))
            self.speed_row.addWidget(b)
            self.speed_btns.append((k, b))
        self.b_step = QPushButton("Шаг кадра")
        self.b_step.setToolTip("Игра на паузе продвигается ровно на один кадр")
        self.b_step.clicked.connect(lambda: self._send("step"))
        self.speed_row.addWidget(self.b_step)
        wv.addLayout(self.speed_row)

        self.filter = QLineEdit()
        self.filter.setPlaceholderText("фильтр по имени…")
        self.filter.setClearButtonEnabled(True)
        self.filter.textChanged.connect(self._apply_filter)
        wv.addWidget(self.filter)

        self.table = QTableWidget(0, 4)
        self.table.setHorizontalHeaderLabels(["Раздел", "Имя", "Значение", "Заморозка"])
        self.table.verticalHeader().setVisible(False)
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        hh = self.table.horizontalHeader()
        hh.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        hh.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        hh.setSectionResizeMode(2, QHeaderView.ResizeMode.Interactive)
        hh.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        self.table.setColumnWidth(2, 180)
        self.table.itemChanged.connect(self._edited)
        wv.addWidget(self.table, 1)
        v.addWidget(self.work, 1)
        from tmstudio.theme import ICON_DIR
        from tmstudio.widgets import EmptyGuide

        self.guide = EmptyGuide(
            os.path.join(ICON_DIR, "m_sleep.png"),
            "Игра пока не на связи",
            "Пульт показывает значения запущенной игры и меняет их прямо отсюда — удобно, когда игра "
            "на втором мониторе или в полноэкранном режиме. Меню поверх игры открывать не нужно.",
            [
                ("Запусти игру", "с установленным тест-меню (HTML5, RPG Maker, Twine или Ren'Py)"),
                ("Включи пульт", "веб-меню: вкладка «Игра» → «Пульт»; Ren'Py: «Настройки» → «Для тестера»"),
                ("Игра появится здесь", "сама, через секунду: значения, заморозки, темп и шаг кадра"),
            ],
        )
        self.guide.hide()
        v.addWidget(self.guide, 1)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.refresh)
        self.timer.start(500)
        self.refresh()

    # ---------------------------------------------------------- игры
    def refresh(self):
        if self.br.server is None:
            self.info.setText(
                "Мост не запущен: порт %d занят (%s). Закрой другую студию." % (tmbridge.PORT, self.br.error)
            )
            return
        games = self.br.games()
        ids = [g[0] for g in games]
        if ids != [self.combo.itemData(i) for i in range(self.combo.count())]:
            self.combo.blockSignals(True)
            self.combo.clear()
            for cid, st, alive in games:
                self.combo.addItem(
                    "%s  |  %s  |  %s"
                    % (st.get("title") or cid, st.get("engine") or "?", "на связи" if alive else "нет связи"),
                    cid,
                )
            if self.cid in ids:
                self.combo.setCurrentIndex(ids.index(self.cid))
            self.combo.blockSignals(False)
            if self.cid not in ids:
                self.cid = ids[0] if ids else None
                self.keys = []
        if not games:
            self.info.setText(
                "Игр на связи нет. В меню игры включи «Пульт в студии»: веб-меню (HTML5, RPG Maker, Twine) — "
                "вкладка «Игра», Ren'Py — «Настройки». Студия слушает 127.0.0.1:%d." % tmbridge.PORT
            )
            self.table.setRowCount(0)
            self.info.hide()
            self.work.hide()
            self.guide.show()
            return
        self.info.show()
        self.work.show()
        self.guide.hide()
        state = dict((g[0], g) for g in games).get(self.cid)
        if state is None:
            return
        _cid, st, alive = state
        caps = st.get("caps") or []
        for k, b in self.speed_btns:
            b.setVisible("speed" in caps)
            b.setObjectName("primary" if "speed" in caps and st.get("speed") == k else "")
            b.style().unpolish(b)
            b.style().polish(b)
        self.b_step.setVisible("step" in caps)
        rows = st.get("rows") or []
        self.info.setText(
            "%s: значений %d. Двойной щелчок по значению — правка, галочка — заморозка%s."
            % (
                "На связи" if alive else "Связь потеряна",
                len(rows),
                "" if alive else " (игра закрыта или меню выключило пульт)",
            )
        )
        self._fill(rows, alive)

    def _pick(self, i):
        self.cid = self.combo.itemData(i)
        self.keys = []
        self.refresh()

    # ---------------------------------------------------------- таблица
    def _fill(self, rows, alive):
        keys = [r.get("k") for r in rows]
        editing = self.table.state() == QAbstractItemView.State.EditingState
        self._filling = True
        try:
            if keys != self.keys:
                if editing:
                    return
                self.keys = keys
                self.table.setRowCount(len(rows))
                for i, r in enumerate(rows):
                    a = QTableWidgetItem(r.get("sec") or "")
                    a.setFlags(a.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    a.setForeground(QColor(MUTE))
                    b = QTableWidgetItem(r.get("name") or r.get("k"))
                    b.setFlags(b.flags() & ~Qt.ItemFlag.ItemIsEditable)
                    b.setToolTip(r.get("k"))
                    c = QTableWidgetItem("")
                    d = QTableWidgetItem("")
                    d.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                    for col, it in enumerate((a, b, c, d)):
                        self.table.setItem(i, col, it)
                self._apply_filter()
            for i, r in enumerate(rows):
                c = self.table.item(i, 2)
                if not (editing and self.table.currentRow() == i):
                    t = _text(r.get("v"))
                    if c.text() != t:
                        c.setText(t)
                c.setForeground(QColor(GOOD if alive else DIM))
                fz = Qt.CheckState.Checked if r.get("fz") else Qt.CheckState.Unchecked
                if self.table.item(i, 3).checkState() != fz:
                    self.table.item(i, 3).setCheckState(fz)
        finally:
            self._filling = False

    def _apply_filter(self):
        q = self.filter.text().strip().lower()
        for i in range(self.table.rowCount()):
            name = (self.table.item(i, 1).text() + " " + self.table.item(i, 0).text()).lower()
            self.table.setRowHidden(i, bool(q) and q not in name)

    def _edited(self, item):
        if self._filling or self.cid is None or item.row() >= len(self.keys):
            return
        k = self.keys[item.row()]
        if item.column() == 2:
            self._send("set", k, item.text())
        elif item.column() == 3:
            self._send("freeze" if item.checkState() == Qt.CheckState.Checked else "unfreeze", k)

    def _send(self, op, k=None, v=None):
        if self.cid is not None:
            self.br.send(self.cid, op, k, v)
