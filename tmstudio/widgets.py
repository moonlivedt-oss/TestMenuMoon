"""Детали новой компоновки студии: карточки игр в списке, полоса разделов, журнал строкой,
окно «что изменится», приветствие первого запуска, образцы цвета меню."""

import html
import re

from PyQt6.QtCore import QRect, QRectF, QSize, Qt, pyqtSignal
from PyQt6.QtGui import QColor, QFont, QFontMetrics, QPainter, QPen
from PyQt6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QPushButton,
    QStyle,
    QStyledItemDelegate,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from tmstudio.theme import (
    ACCENT,
    ACCENT_LINE,
    ACCENT_SOFT,
    BG2,
    BG3,
    DIM,
    GOOD,
    MUTE,
    TXT,
    TXT2,
    WARN,
    WHITE,
    ibtn,
    icon,
)
from tmstudio.tokens import ENGINE, TOK

# роль данных строки списка игр: dict(title, engine, engine_name, counts, status, dirty)
GAME_ROLE = Qt.ItemDataRole.UserRole + 1

# готовые цвета меню (те же, что в «Настройках» меню Ren'Py)
ACCENT_PRESETS = [
    ("Бирюза", "#38e0c8"),
    ("Голубой", "#4aa8ff"),
    ("Розовый", "#ff6b9d"),
    ("Зелёный", "#5ad469"),
    ("Оранж", "#ff9f43"),
    ("Фиолет", "#b06bff"),
    ("Красный", "#ff5c5c"),
    ("Белый", "#e7ebf2"),
]


def _qcolor(hex6, alpha=255):
    c = QColor(hex6[:7])
    c.setAlpha(alpha)
    return c


def engine_pill(key, fallback):
    """(подпись, цвет текста, цвет фона) плашки движка."""
    if key in ENGINE:
        name, fg, _bg = ENGINE[key]
        return name, _qcolor(fg), _qcolor(fg, 46)
    return fallback, QColor(TXT2), _qcolor(TXT2, 30)


# ================================================================ карточки игр
class GameDelegate(QStyledItemDelegate):
    """Рисует строку списка игр карточкой: точка статуса, название, плашка движка, счётчики."""

    H = 58

    def sizeHint(self, option, index):
        return QSize(option.rect.width(), self.H)

    def paint(self, p, opt, index):
        d = index.data(GAME_ROLE) or {}
        r = QRectF(opt.rect.adjusted(2, 3, -2, -3))
        sel = bool(opt.state & QStyle.StateFlag.State_Selected)
        hov = bool(opt.state & QStyle.StateFlag.State_MouseOver)
        p.save()
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if sel:
            p.setPen(QPen(QColor(ACCENT_LINE_HEX), 1))
            p.setBrush(QColor(ACCENT_SOFT_HEX))
            p.drawRoundedRect(r, 10, 10)
        elif hov:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(BG3))
            p.drawRoundedRect(r, 10, 10)

        # точка статуса: зелёная — меню свежее, жёлтая — устарело, пустая — нет меню
        st = d.get("status", "none")
        cx, cy = r.left() + 16, r.center().y()
        if st == "none":
            p.setPen(QPen(QColor(MUTE), 1.5))
            p.setBrush(Qt.BrushStyle.NoBrush)
        else:
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(GOOD if st == "ok" else WARN))
        p.drawEllipse(QRectF(cx - 4.5, cy - 4.5, 9, 9))

        x = int(r.left() + 32)
        w = int(r.right() - x - 8)
        f = QFont(opt.font)
        f.setPointSizeF(10.5)
        f.setWeight(QFont.Weight.DemiBold if sel else QFont.Weight.Medium)
        p.setFont(f)
        p.setPen(QColor(WHITE if sel else (TXT if st != "none" else TXT2)))
        fm = QFontMetrics(f)
        title = fm.elidedText(d.get("title", ""), Qt.TextElideMode.ElideRight, w)
        p.drawText(QRect(x, int(r.top() + 7), w, fm.height()), Qt.AlignmentFlag.AlignLeft, title)

        # вторая строка: плашка движка + счётчики (+ «не сохранено»)
        f2 = QFont(opt.font)
        f2.setPointSizeF(8.5)
        p.setFont(f2)
        fm2 = QFontMetrics(f2)
        y2 = int(r.top() + 9 + fm.height())
        name, fg, bg = engine_pill(d.get("engine"), d.get("engine_name", ""))
        pw = fm2.horizontalAdvance(name) + 12
        pill = QRectF(x, y2, pw, fm2.height() + 4)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(bg)
        p.drawRoundedRect(pill, 6, 6)
        p.setPen(fg)
        p.drawText(pill, Qt.AlignmentFlag.AlignCenter, name)
        tx = int(x + pw + 8)
        rest = d.get("counts", "")
        if rest:
            p.setPen(QColor(DIM))
            p.drawText(
                QRect(tx, y2 + 2, w - pw - 8, fm2.height()),
                Qt.AlignmentFlag.AlignLeft,
                fm2.elidedText(rest, Qt.TextElideMode.ElideRight, w - pw - 8),
            )
            tx += fm2.horizontalAdvance(rest) + 10
        if d.get("dirty"):
            p.setPen(QColor(WARN))
            p.drawText(
                QRect(tx, y2 + 2, max(0, int(r.right()) - tx), fm2.height()), Qt.AlignmentFlag.AlignLeft, "не сохранено"
            )
        p.restore()


# QPen/QBrush не понимают rgba(...) из QSS — те же цвета в виде QColor-строк
_ac = QColor(ACCENT)
ACCENT_SOFT_HEX = QColor(_ac.red(), _ac.green(), _ac.blue(), 36).name(QColor.NameFormat.HexArgb)
ACCENT_LINE_HEX = QColor(_ac.red(), _ac.green(), _ac.blue(), 140).name(QColor.NameFormat.HexArgb)
assert ACCENT_SOFT and ACCENT_LINE  # те же оттенки, что в QSS


# ================================================================ полоса разделов
class NavRail(QWidget):
    """Узкая полоса слева: разделы студии. changed(int) — выбран раздел."""

    changed = pyqtSignal(int)

    def __init__(self, items, bottom=()):
        super().__init__()
        self.setObjectName("rail")
        self.setFixedWidth(84)
        v = QVBoxLayout(self)
        v.setContentsMargins(8, 12, 8, 12)
        v.setSpacing(6)
        self.group = QButtonGroup(self)
        self.group.setExclusive(True)
        self.buttons = []
        for i, (text, name, tip) in enumerate(items):
            b = self._btn(text, name, tip)
            b.setCheckable(True)
            self.group.addButton(b, i)
            v.addWidget(b)
            self.buttons.append(b)
        v.addStretch(1)
        self.extra = []
        for text, name, tip, fn in bottom:
            b = self._btn(text, name, tip)
            b.clicked.connect(fn)
            v.addWidget(b)
            self.extra.append(b)
        self.group.idClicked.connect(self.changed.emit)
        if self.buttons:
            self.buttons[0].setChecked(True)

    def _btn(self, text, name, tip):
        b = QToolButton()
        b.setObjectName("nav")
        b.setText(text)
        b.setIcon(icon(name))
        b.setIconSize(QSize(28, 28))
        b.setToolTip(tip)
        b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setFixedWidth(68)
        return b

    def select(self, i):
        self.buttons[i].setChecked(True)


# ================================================================ журнал строкой
class LogPanel(QWidget):
    """Строка состояния с последним сообщением; по щелчку — весь журнал (self.log).
    Ошибка раскрывает журнал сама."""

    def __init__(self, on_stop):
        super().__init__()
        v = QVBoxLayout(self)
        v.setContentsMargins(0, 8, 0, 0)
        v.setSpacing(6)
        bar = QFrame(objectName="statusbar")
        h = QHBoxLayout(bar)
        h.setContentsMargins(12, 6, 6, 6)
        h.setSpacing(8)
        self.dot = QLabel()
        self.dot.setFixedSize(10, 10)
        self.last = QLabel("Готово к работе", objectName="dim")
        self.last.setMinimumWidth(10)
        h.addWidget(self.dot)
        h.addWidget(self.last, 1)
        self.b_stop = ibtn("Стоп", "close", "Прервать текущую команду и очистить очередь", px=16)
        self.b_stop.setObjectName("danger")
        self.b_stop.setEnabled(False)
        self.b_stop.clicked.connect(on_stop)
        self.b_clear = QPushButton("Очистить")
        self.b_toggle = QPushButton("Журнал  ▴")
        self.b_toggle.setCheckable(True)
        self.b_toggle.toggled.connect(self.set_open)
        for b in (self.b_stop, self.b_clear, self.b_toggle):
            h.addWidget(b)
        v.addWidget(bar)
        self.log = QPlainTextEdit()
        self.log.setObjectName("log")
        self.log.setReadOnly(True)
        self.log.setMinimumHeight(180)
        self.log.hide()
        self.b_clear.clicked.connect(self.log.clear)
        v.addWidget(self.log)
        self._set_dot(TOK["text_off"])

    def _set_dot(self, color):
        self.dot.setStyleSheet(f"background:{color}; border-radius:5px;")

    def set_open(self, on):
        self.log.setVisible(on)
        self.b_toggle.setText("Журнал  ▾" if on else "Журнал  ▴")
        if self.b_toggle.isChecked() != on:
            self.b_toggle.setChecked(on)

    def show_line(self, text, color):
        t = re.sub(r"\s+", " ", text).strip()
        if not t:
            return
        fm = QFontMetrics(self.last.font())
        self.last.setText(fm.elidedText(t, Qt.TextElideMode.ElideRight, max(80, self.last.width())))
        self.last.setToolTip(html.escape(t))
        self.last.setStyleSheet(f"color:{color};")
        self._set_dot(color)
        if color == TOK["err"]:
            self.set_open(True)


# ================================================================ «что изменится»
class ApplyPreview(QDialog):
    """Что поменяется в игре перед «Применить в игре». lines: [(знак, текст, пояснение)],
    знак: "+" добавится, "-" уберётся, "~" обновится."""

    SIGN = {"+": TOK["ok"], "-": TOK["err"], "~": TOK["warn"]}

    def __init__(self, parent, title, lines, note=""):
        super().__init__(parent)
        self.setWindowTitle("Что изменится")
        self.setMinimumWidth(460)
        v = QVBoxLayout(self)
        v.setContentsMargins(18, 16, 18, 14)
        v.setSpacing(8)
        v.addWidget(QLabel(title, objectName="h2"))
        v.addWidget(QLabel("Файлы самой игры не меняются, только файлы меню.", objectName="dim"))
        box = QFrame(objectName="card")
        bl = QVBoxLayout(box)
        bl.setContentsMargins(12, 10, 12, 10)
        bl.setSpacing(4)
        for sign, text, detail in lines[:40]:
            row = QHBoxLayout()
            s = QLabel({"-": "−"}.get(sign, sign))
            s.setFixedWidth(16)
            s.setStyleSheet(f"color:{self.SIGN.get(sign, TXT)}; font-weight:700;")
            t = QLabel(text)
            if sign == "-":
                t.setStyleSheet(f"color:{DIM}; text-decoration: line-through;")
            row.addWidget(s)
            row.addWidget(t, 1)
            if detail:
                row.addWidget(QLabel(detail, objectName="dim"))
            bl.addLayout(row)
        if len(lines) > 40:
            bl.addWidget(QLabel(f"… и ещё {len(lines) - 40}", objectName="dim"))
        v.addWidget(box)
        if note:
            n = QLabel(note)
            n.setWordWrap(True)
            n.setObjectName("warnbox")
            v.addWidget(n)
        self.ask = QCheckBox("Больше не спрашивать (показывать только в журнале)")
        v.addWidget(self.ask)
        h = QHBoxLayout()
        h.addStretch(1)
        b_no = QPushButton("Отмена")
        b_no.clicked.connect(self.reject)
        b_ok = QPushButton("Применить")
        b_ok.setObjectName("primary")
        b_ok.setDefault(True)
        b_ok.clicked.connect(self.accept)
        h.addWidget(b_no)
        h.addWidget(b_ok)
        v.addLayout(h)


# ================================================================ первый запуск
class WelcomePage(QWidget):
    """Пустой список игр: три шага и одна главная кнопка."""

    def __init__(self, logo_path, on_folder, on_add, on_quick, on_tour):
        super().__init__()
        outer = QVBoxLayout(self)
        outer.addStretch(1)
        card = QFrame(objectName="welcome")
        card.setMaximumWidth(640)
        v = QVBoxLayout(card)
        v.setContentsMargins(32, 28, 32, 24)
        v.setSpacing(10)
        if logo_path:
            from PyQt6.QtGui import QPixmap

            pic = QLabel()
            pic.setPixmap(
                QPixmap(logo_path).scaled(
                    64, 64, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation
                )
            )
            pic.setAlignment(Qt.AlignmentFlag.AlignCenter)
            v.addWidget(pic)
        t = QLabel("Тест-меню для твоих игр", objectName="h1")
        t.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(t)
        s = QLabel("Значения, перемотка и проверка сюжета прямо внутри игры", objectName="dim")
        s.setAlignment(Qt.AlignmentFlag.AlignCenter)
        v.addWidget(s)
        steps = QHBoxLayout()
        steps.setSpacing(10)
        for n, head, sub in (
            ("Шаг 1", "Укажи папку", "где лежат игры"),
            ("Шаг 2", "Студия найдёт", "движок и версию"),
            ("Шаг 3", "Ставь меню", "в одну или во все"),
        ):
            c = QFrame(objectName="card")
            cl = QVBoxLayout(c)
            cl.setContentsMargins(12, 10, 12, 10)
            cl.setSpacing(2)
            a = QLabel(n)
            a.setStyleSheet(f"color:{ACCENT}; font-weight:700; font-size:8.5pt;")
            cl.addWidget(a)
            cl.addWidget(QLabel(head, objectName="strong"))
            cl.addWidget(QLabel(sub, objectName="dim"))
            steps.addWidget(c)
        v.addSpacing(8)
        v.addLayout(steps)
        v.addSpacing(10)
        h = QHBoxLayout()
        h.addStretch(1)
        b1 = ibtn("Выбрать папку с играми", "load")
        b1.setObjectName("primary")
        b1.clicked.connect(on_folder)
        b2 = QPushButton("Добавить одну игру")
        b2.clicked.connect(on_add)
        b3 = QPushButton("Быстрая установка")
        b3.setToolTip("Поставить меню в любую игру без добавления в список")
        b3.clicked.connect(on_quick)
        for b in (b1, b2, b3):
            h.addWidget(b)
        h.addStretch(1)
        v.addLayout(h)
        tour = QPushButton("Показать тур по студии")
        tour.setObjectName("link")
        tour.setCursor(Qt.CursorShape.PointingHandCursor)
        tour.clicked.connect(on_tour)
        v.addWidget(tour, 0, Qt.AlignmentFlag.AlignCenter)
        row = QHBoxLayout()
        row.addStretch(1)
        row.addWidget(card, 10)
        row.addStretch(1)
        outer.addLayout(row)
        outer.addStretch(2)


# ================================================================ цвет меню
class AccentPicker(QWidget):
    """Готовые цвета + «как у всех» + свой. value() — "#rrggbb" или "" (общий цвет)."""

    changed = pyqtSignal()

    def __init__(self, default_accent, on_custom):
        super().__init__()
        self.default = default_accent
        self._value = ""
        h = QHBoxLayout(self)
        h.setContentsMargins(0, 0, 0, 0)
        h.setSpacing(6)
        self.b_inherit = QPushButton("как у всех")
        self.b_inherit.setObjectName("chip")
        self.b_inherit.setCheckable(True)
        self.b_inherit.setToolTip(f"Общий цвет всех игр ({default_accent})")
        self.b_inherit.clicked.connect(lambda: self.set_value("", user=True))
        h.addWidget(self.b_inherit)
        self.sw = []
        for name, col in ACCENT_PRESETS:
            b = QPushButton()
            b.setObjectName("swatch")
            b.setFixedSize(24, 24)
            b.setToolTip(f"{name} {col}")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.clicked.connect(lambda _=False, c=col: self.set_value(c, user=True))
            b._col = col
            h.addWidget(b)
            self.sw.append(b)
        self.b_custom = QPushButton("свой…")
        self.b_custom.setObjectName("chip")
        self.b_custom.clicked.connect(on_custom)
        h.addWidget(self.b_custom)
        h.addStretch(1)
        self._paint()

    def value(self):
        return self._value

    def set_value(self, v, user=False):
        self._value = (v or "").strip()
        self._paint()
        if user:
            self.changed.emit()

    def _paint(self):
        cur = self._value.lower()
        self.b_inherit.setChecked(not cur)
        for b in self.sw:
            on = b._col.lower() == cur
            b.setStyleSheet(
                f"QPushButton#swatch {{ background:{b._col}; border-radius:7px;"
                f" border:2px solid {WHITE if on else BG2}; padding:0; }}"
            )
        custom = bool(cur) and cur not in [c.lower() for _n, c in ACCENT_PRESETS]
        self.b_custom.setText(f"свой: {self._value}" if custom else "свой…")
        self.b_custom.setStyleSheet(f"QPushButton#chip {{ border:1px solid {self._value}; }}" if custom else "")
