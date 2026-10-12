"""Внешний вид студии: палитра, таблица стилей (QSS), значки и мелкие виджеты-помощники."""

import os

from PyQt6.QtCore import Qt, QSize
from PyQt6.QtGui import QColor, QIcon, QPixmap, QPainter
from PyQt6.QtWidgets import (
    QWidget,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QFrame,
    QGraphicsDropShadowEffect,
)

from tmkit import games

from tmstudio import ROOT
from tmstudio.tokens import ENGINE, TOK

ASSETS = os.path.join(ROOT, "assets")
ICON_PATH = os.path.join(ASSETS, "tm_icon.png")
ICON_DIR = os.path.join(ASSETS, "icons")  # наклейки из библиотеки (tools/make_icons.py)

ACCENT = getattr(games, "ACCENT", TOK["accent"])

# короткие ярлыки движков для списка игр
ENGINE_BADGE = {k: v[0] for k, v in ENGINE.items()}

# ------------------------------------------------------------------ палитра
# Слоистая тёмная тема: BG0 (окно) < BG1 (панели) < BG2 (карточки) < BG3 (контролы).
# Значения — из общего набора (tmstudio/tokens.py, собран tools/gen_tokens.py).
BG0, BG1, BG2, BG3 = TOK["bg_window"], TOK["bg_panel"], TOK["bg_card"], TOK["bg_control"]
BG_DEEP = TOK["bg_deep"]
LINE, LINE2 = TOK["line_soft"], TOK["line"]
TXT, DIM, MUTE = TOK["text"], TOK["text_hint"], TOK["text_off"]
TXT2, WHITE = TOK["text_dim"], TOK["text_bright"]
DANGER, GOOD, WARN = TOK["err"], TOK["ok"], TOK["warn"]

_ac = QColor(ACCENT)
ACCENT2 = _ac.lighter(122).name()  # светлее — верх градиента
ACCENT_DK = _ac.darker(140).name()  # темнее — для рамок акцента
ACCENT_INK = TOK["on_accent"] if _ac.lightnessF() > 0.45 else TOK["on_accent_light"]  # текст на акценте
_r, _g, _b = _ac.red(), _ac.green(), _ac.blue()
ACCENT_SOFT = f"rgba({_r},{_g},{_b},0.14)"  # мягкая заливка (ховер/фокус)
ACCENT_LINE = f"rgba({_r},{_g},{_b},0.55)"

_GRAD_ACC = f"qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {ACCENT2}, stop:1 {ACCENT})"

# ------------------------------------------------------------------ стиль
QSS = f"""
* {{ font-family: "Segoe UI","Inter"; font-size: 10pt; color: {TXT}; }}
QMainWindow, QWidget {{ background: {BG0}; }}
QLabel {{ background: transparent; }}
QLabel#h1 {{ font-size: 17pt; font-weight: 800; color: {WHITE}; letter-spacing: 0.3px; }}
QLabel#sub {{ color: {MUTE}; font-size: 9pt; }}
QLabel#dim {{ color: {DIM}; }}
QLabel#accent {{ color: {ACCENT}; font-weight: 700; }}
QLabel#section {{ color: {MUTE}; font-size: 8.5pt; font-weight: 700; letter-spacing: 1.2px; }}

QListWidget {{
    background: {BG1}; border: 1px solid {LINE}; border-radius: 14px;
    padding: 7px; outline: 0;
}}
QListWidget::item {{ padding: 10px 12px; border-radius: 10px; margin: 2px 0; color: {DIM}; }}
QListWidget::item:selected {{ background: {ACCENT_SOFT}; color: {WHITE};
    border: 1px solid {ACCENT_LINE}; }}
QListWidget::item:hover {{ background: {BG3}; color: {TXT}; }}

QTabWidget::pane {{
    border: 1px solid {LINE}; border-radius: 14px; top: -1px; background: {BG1};
}}
QTabBar {{ qproperty-drawBase: 0; }}
QTabBar::tab {{
    background: transparent; color: {DIM}; padding: 9px 18px; margin-right: 4px;
    border: 1px solid transparent; border-radius: 10px;
}}
QTabBar::tab:selected {{ color: {WHITE}; background: {ACCENT_SOFT}; border: 1px solid {ACCENT_LINE}; font-weight: 700; }}
QTabBar::tab:hover:!selected {{ color: {WHITE}; background: {BG2}; }}
QTabBar::tab:disabled {{ color: {MUTE}; }}

QLineEdit, QPlainTextEdit {{
    background: {BG0}; border: 1px solid {LINE}; border-radius: 10px;
    padding: 8px 10px; selection-background-color: {ACCENT}; selection-color: {ACCENT_INK};
}}
QLineEdit:hover, QPlainTextEdit:hover {{ border: 1px solid {LINE2}; }}
QLineEdit:focus, QPlainTextEdit:focus {{ border: 1px solid {ACCENT}; background: {BG1}; }}

QPushButton {{
    background: {BG3}; border: 1px solid {LINE2}; border-radius: 10px;
    padding: 9px 15px; color: {TXT}; font-weight: 600;
}}
QPushButton:hover {{ background: {BG2}; border: 1px solid {ACCENT_LINE}; }}
QPushButton:pressed {{ background: {ACCENT}; color: {ACCENT_INK}; border: 1px solid {ACCENT}; }}
QPushButton:disabled {{ color: {MUTE}; background: {BG1}; border: 1px solid {LINE}; }}
QPushButton#primary {{ background: {_GRAD_ACC}; color: {ACCENT_INK}; font-weight: 800; border: 0; }}
QPushButton#primary:hover {{ background: {ACCENT2}; }}
QPushButton#primary:pressed {{ background: {ACCENT_DK}; }}
QPushButton#danger:hover {{ border: 1px solid {DANGER}; color: {DANGER}; }}
QPushButton:focus {{ border: 1px solid {ACCENT}; }}
QPushButton#primary:focus {{ border: 2px solid {ACCENT_INK}; }}

QTableWidget {{
    background: {BG0}; border: 1px solid {LINE}; border-radius: 12px;
    gridline-color: {LINE}; selection-background-color: {ACCENT_SOFT}; selection-color: {WHITE};
    alternate-background-color: {BG1};
}}
QHeaderView::section {{
    background: {BG2}; color: {DIM}; padding: 8px; border: 0;
    border-bottom: 1px solid {LINE}; font-weight: 700;
}}
QTableWidget::item {{ padding: 5px; }}
QTableWidget::item:selected {{ border: 0; }}

QPlainTextEdit#log {{
    font-family: "Cascadia Mono","Consolas","Courier New"; font-size: 9.5pt;
    color: {TXT2}; background: {BG_DEEP}; border: 1px solid {LINE}; border-radius: 12px;
}}
QSplitter::handle {{ background: transparent; }}
QSplitter::handle:horizontal {{ width: 10px; }}
QSplitter::handle:vertical {{ height: 10px; }}

QScrollBar:vertical {{ background: transparent; width: 12px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {LINE2}; border-radius: 5px; min-height: 28px; }}
QScrollBar::handle:vertical:hover {{ background: {ACCENT}; }}
QScrollBar:horizontal {{ background: transparent; height: 12px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {LINE2}; border-radius: 5px; min-width: 28px; }}
QScrollBar::handle:horizontal:hover {{ background: {ACCENT}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: transparent; }}

/* ---- новая компоновка: полоса разделов, карточки, шапка игры, журнал строкой ---- */
QWidget#rail {{ background: {BG1}; border-right: 1px solid {LINE}; }}
QToolButton#nav {{
    background: transparent; border: 0; border-radius: 12px; padding: 7px 2px 6px 2px;
    color: {DIM}; font-size: 8.5pt; font-weight: 600;
}}
QToolButton#nav:hover {{ background: {BG2}; color: {TXT}; }}
QToolButton#nav:checked {{ background: {ACCENT_SOFT}; color: {WHITE}; }}
QLabel#h1 {{ font-size: 15pt; font-weight: 700; color: {WHITE}; }}
QLabel#h2 {{ font-size: 12pt; font-weight: 700; color: {WHITE}; }}
QLabel#strong {{ font-weight: 700; color: {TXT}; }}
QListWidget#games {{ background: transparent; border: 0; padding: 0; }}
QListWidget#games::item {{ padding: 0; margin: 0; border: 0; background: transparent; }}
QPushButton#iconbtn {{ background: transparent; border: 0; padding: 4px; border-radius: 8px; }}
QPushButton#iconbtn:hover {{ background: {BG3}; }}
QToolButton#more {{
    background: {BG3}; border: 1px solid {LINE2}; border-radius: 10px;
    padding: 7px 12px; color: {TXT}; font-weight: 800;
}}
QToolButton#more:hover {{ border: 1px solid {ACCENT_LINE}; }}
QToolButton#more::menu-indicator {{ image: none; width: 0; }}
QMenu {{ background: {BG2}; border: 1px solid {LINE2}; border-radius: 10px; padding: 6px; }}
QMenu::item {{ padding: 7px 18px 7px 10px; border-radius: 7px; color: {TXT}; }}
QMenu::item:selected {{ background: {ACCENT_SOFT}; color: {WHITE}; }}
QMenu::item:disabled {{ color: {MUTE}; }}
QMenu::separator {{ height: 1px; background: {LINE}; margin: 5px 6px; }}
QMenu::icon {{ padding-left: 6px; }}
QFrame#statusbar {{ background: {BG1}; border: 1px solid {LINE}; border-radius: 12px; }}
QFrame#card {{ background: {BG2}; border: 1px solid {LINE}; border-radius: 12px; }}
QFrame#welcome {{ background: {BG1}; border: 1px solid {LINE}; border-radius: 16px; }}
QFrame#warnbar {{ background: rgba(255,180,84,0.10); border: 1px solid rgba(255,180,84,0.5); border-radius: 12px; }}
QLabel#warnbox {{
    background: rgba(255,180,84,0.10); color: {WARN}; border: 1px solid rgba(255,180,84,0.4);
    border-radius: 10px; padding: 8px 10px;
}}
QPushButton#chip {{ padding: 4px 10px; border-radius: 9px; font-weight: 600; }}
QPushButton#chip:checked {{ background: {ACCENT_SOFT}; border: 1px solid {ACCENT_LINE}; color: {WHITE}; }}
QPushButton#link {{ background: transparent; border: 0; color: {DIM}; font-weight: 500; padding: 4px; }}
QPushButton#link:hover {{ color: {ACCENT}; background: transparent; border: 0; }}
QCheckBox {{ color: {DIM}; spacing: 8px; }}
QDialog {{ background: {BG1}; }}

QToolTip {{
    background: {BG2}; color: {TXT}; border: 1px solid {ACCENT_LINE};
    border-radius: 8px; padding: 6px 9px;
}}
QMessageBox, QInputDialog, QColorDialog {{ background: {BG1}; }}
"""


_ICON_CACHE = {}


def icon(name):
    """QIcon из assets/icons/<name>.png; нет файла — пустой значок (кнопка остаётся с текстом)."""
    if name not in _ICON_CACHE:
        p = os.path.join(ICON_DIR, name + ".png")
        _ICON_CACHE[name] = QIcon(p) if os.path.exists(p) else QIcon()
    return _ICON_CACHE[name]


def faded_icon(name, opacity=0.28):
    """Приглушённая копия значка (статус «не установлено» в списке игр)."""
    key = f"{name}@{opacity}"
    if key not in _ICON_CACHE:
        src = icon(name).pixmap(64, 64)
        out = QPixmap(src.size())
        out.fill(Qt.GlobalColor.transparent)
        pt = QPainter(out)
        pt.setOpacity(opacity)
        pt.drawPixmap(0, 0, src)
        pt.end()
        _ICON_CACHE[key] = QIcon(out)
    return _ICON_CACHE[key]


def ibtn(text, name, tip=None, px=20):
    """QPushButton со значком."""
    b = QPushButton(text)
    b.setIcon(icon(name))
    b.setIconSize(QSize(px, px))
    if tip:
        b.setToolTip(tip)
    return b


def mascot_box(name, text):
    """Пустое состояние: маскот + пояснение (скрыт, пока есть что показать)."""
    w = QWidget()
    h = QHBoxLayout(w)
    h.setContentsMargins(10, 10, 10, 10)
    h.setSpacing(14)
    p = os.path.join(ICON_DIR, name + ".png")
    if os.path.exists(p):
        pic = QLabel()
        pic.setPixmap(
            QPixmap(p).scaled(
                72,
                72,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        h.addWidget(pic, 0, Qt.AlignmentFlag.AlignTop)
    lb = QLabel(text, objectName="dim")
    lb.setWordWrap(True)
    h.addWidget(lb, 1)
    w.label = lb
    return w


# пометка несохранённых правок у игры в списке
DIRTY_MARK = "  (не сохранено)"


def short_title(title):
    """Название игры для списка: без служебного «TEST MENU |» в начале."""
    t = (title or "").strip()
    if t.upper().startswith("TEST MENU"):
        t = t[len("TEST MENU"):].lstrip(" |:—-")
    return t or "без названия"


def hline():
    f = QFrame()
    f.setFrameShape(QFrame.Shape.HLine)
    f.setStyleSheet(f"color:{LINE};")
    return f


def add_shadow(w, blur=22, dy=5, alpha=150):
    """Мягкая тень под виджетом (для leaf-виджетов — иконка, карточка)."""
    eff = QGraphicsDropShadowEffect(w)
    eff.setBlurRadius(blur)
    eff.setOffset(0, dy)
    eff.setColor(QColor(0, 0, 0, alpha))
    w.setGraphicsEffect(eff)
