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

ASSETS = os.path.join(ROOT, "assets")
ICON_PATH = os.path.join(ASSETS, "tm_icon.png")
ICON_DIR = os.path.join(ASSETS, "icons")  # наклейки из библиотеки (tools/make_icons.py)

ACCENT = getattr(games, "ACCENT", "#38e0c8")

# короткие ярлыки движков для списка игр
ENGINE_BADGE = {"renpy": "Ren'Py", "twine": "Twine", "rpgmaker": "RPG Maker", "godot": "Godot", "unity": "Unity", "web": "HTML5", "unreal": "Unreal", "gamemaker": "GameMaker"}

# ------------------------------------------------------------------ палитра
# Слоистая тёмная тема: BG0 (окно) < BG1 (панели) < BG2 (карточки) < BG3 (контролы).
BG0, BG1, BG2, BG3 = "#0b0e14", "#10141d", "#161b26", "#1e2432"
LINE, LINE2 = "#242c3a", "#313a4c"
TXT, DIM, MUTE = "#e7ebf2", "#8b93a3", "#5b6373"
DANGER, GOOD, WARN = "#ff6b6b", "#5ad469", "#f0b429"

_ac = QColor(ACCENT)
ACCENT2 = _ac.lighter(122).name()  # светлее — верх градиента
ACCENT_DK = _ac.darker(140).name()  # темнее — для рамок акцента
ACCENT_INK = "#07110f" if _ac.lightnessF() > 0.45 else "#e7fffb"  # текст на акценте
_r, _g, _b = _ac.red(), _ac.green(), _ac.blue()
ACCENT_SOFT = f"rgba({_r},{_g},{_b},0.14)"  # мягкая заливка (ховер/фокус)
ACCENT_LINE = f"rgba({_r},{_g},{_b},0.55)"

_GRAD_ACC = f"qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {ACCENT2}, stop:1 {ACCENT})"

# ------------------------------------------------------------------ стиль
QSS = f"""
* {{ font-family: "Segoe UI","Inter"; font-size: 10pt; color: {TXT}; }}
QMainWindow, QWidget {{ background: {BG0}; }}
QLabel {{ background: transparent; }}
QLabel#h1 {{ font-size: 17pt; font-weight: 800; color: #ffffff; letter-spacing: 0.3px; }}
QLabel#sub {{ color: {MUTE}; font-size: 9pt; }}
QLabel#dim {{ color: {DIM}; }}
QLabel#accent {{ color: {ACCENT}; font-weight: 700; }}
QLabel#section {{ color: {MUTE}; font-size: 8.5pt; font-weight: 700; letter-spacing: 1.2px; }}

QListWidget {{
    background: {BG1}; border: 1px solid {LINE}; border-radius: 14px;
    padding: 7px; outline: 0;
}}
QListWidget::item {{ padding: 10px 12px; border-radius: 10px; margin: 2px 0; color: {DIM}; }}
QListWidget::item:selected {{ background: {ACCENT_SOFT}; color: #ffffff;
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
QTabBar::tab:selected {{ color: {ACCENT_INK}; background: {_GRAD_ACC}; font-weight: 700; }}
QTabBar::tab:hover:!selected {{ color: #ffffff; background: {BG2}; }}
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
QPushButton#danger:hover {{ border: 1px solid {DANGER}; color: #ffd9d9; }}
QPushButton:focus {{ border: 1px solid {ACCENT}; }}
QPushButton#primary:focus {{ border: 2px solid {ACCENT_INK}; }}

QTableWidget {{
    background: {BG0}; border: 1px solid {LINE}; border-radius: 12px;
    gridline-color: {LINE}; selection-background-color: {ACCENT_SOFT}; selection-color: #ffffff;
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
    color: #cdd3dc; background: #080b11; border: 1px solid {LINE}; border-radius: 12px;
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
                72, 72,
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


