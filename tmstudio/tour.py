"""Обучение в студии: пошаговый тур с подсветкой кнопок.

Поверх окна ложится затемнение с «окошком» вокруг нужного элемента и карточка с маскотом,
заголовком и пояснением. Листать: «Далее»/«Назад», стрелки, Enter, пробел; Esc — закрыть.
Первый запуск студии открывает тур сам (QSettings «tour_done»), дальше — кнопка «Обучение».

Шаг тура: Step(title, text, target, before, mascot). target(studio) возвращает QWidget,
(QWidget, QRect в его координатах) или None (карточка по центру). before(studio) — что
сделать перед показом (переключить вкладку).
"""

import os
from dataclasses import dataclass
from typing import Callable, Optional

from PyQt6.QtCore import Qt, QEvent, QRect, QRectF
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QPen, QPixmap
from PyQt6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from tmstudio.tokens import TOK


@dataclass
class Step:
    title: str
    text: str
    target: Optional[Callable] = None
    before: Optional[Callable] = None
    mascot: str = "m_think"


def _tab(i):
    """Цель — ярлык вкладки i."""
    return lambda st: (st.tabs.tabBar(), st.tabs.tabBar().tabRect(i))


def _go_tab(i):
    def go(st):
        if st.tabs.isTabEnabled(i):
            st.tabs.setCurrentIndex(i)

    return go


def steps():
    return [
        Step(
            "Привет! Это Test Menu Studio",
            "Студия ставит в игры тест-меню. В самой игре меню открывается клавишами "
            "<b>Shift+T</b> или <b>F9</b>.<br><br>Покажу главное за минуту. Листать — "
            "кнопкой «Далее» или стрелками, закрыть — Esc.",
            None,
            mascot="m_wave",
        ),
        Step(
            "Самый быстрый путь",
            "Выбери папку игры — Ren'Py, Godot, Unity, RPG Maker или Twine: движок студия "
            "определит сама, меню встанет само и найдёт статы автоматически.<br><br>"
            "Дальше просто запусти игру и нажми <b>Shift+T</b>.",
            lambda st: st.b_quick,
            mascot="m_party",
        ),
        Step(
            "Список игр",
            "Игры, которые ты добавил для тонкой настройки. Значок слева:<br>"
            "• галочка — меню стоит, версия свежая;<br>"
            "• восклицательный знак — меню устарело, нажми «Применить в игре»;<br>"
            "• бледная галочка — меню ещё не установлено.<br><br>"
            "Пометка «не сохранено» — у игры есть правки, которые ещё не записаны.",
            lambda st: st.list,
            mascot="m_search",
        ),
        Step(
            "Добавить игру",
            "Добавляет игру в список. Для Ren'Py выбери папку <b>game/</b>, для Twine и "
            "RPG Maker — папку игры. Движок студия определит сама, заголовок предложит "
            "по имени папки.<br><br>«Убрать» удаляет игру только из списка, файлы игры "
            "остаются.",
            lambda st: st.b_add_game,
            mascot="m_wrench",
        ),
        Step(
            "Основное",
            "Название в меню, цвет меню, путь к игре и её движок. Пустой цвет — общий для всех игр.",
            _tab(0),
            _go_tab(0),
            mascot="m_think",
        ),
        Step(
            "Главная кнопка",
            "<b>Применить в игре</b> сохраняет правки и ставит меню в игру. "
            "Нажимай после любых изменений.<br><br><b>Ctrl+S</b> только сохраняет "
            "правки, без установки в игру.",
            lambda st: st.overview.b_save_deploy,
            _go_tab(0),
            mascot="m_party",
        ),
        Step(
            "Проверить в игре",
            "<b>Запустить</b> открывает игру, чтобы сразу посмотреть меню.<br><br>"
            "В игре: <b>Shift+T</b> / <b>F9</b> — меню, <b>Shift+H</b> — подсказки к "
            "выборам, <b>Esc</b> — закрыть. Внутри меню есть своя справка — кнопка со "
            "знаком вопроса в шапке.",
            lambda st: st.overview.b_run,
            _go_tab(0),
            mascot="m_wave",
        ),
        Step(
            "Свои статы (по желанию)",
            "Здесь можно задать статы для меню вручную: метка и путь к переменной, "
            "например <b>mc.money</b>, плюс границы min/max.<br><br>"
            "Можно ничего не заполнять — меню и так находит переменные само (режим «авто»).",
            _tab(1),
            _go_tab(1),
            mascot="m_think",
        ),
        Step(
            "Где искать статы",
            "Не знаешь, как в игре называются деньги или симпатия? <b>Всё сразу</b> "
            "распакует игру и найдёт подсказки; после «//» — понятное имя. Нужные строки "
            "выдели и нажми «В статы» — они станут статами с этими именами.<br><br>Для Twine и RPG Maker здесь "
            "одна кнопка — «Найти переменные».",
            lambda st: (
                st.cand_tab.b_full
                if st.cand_tab.b_full.isVisible()
                else (st.tabs.tabBar(), st.tabs.tabBar().tabRect(3))
            ),
            _go_tab(3),
            mascot="m_search",
        ),
        Step(
            "Журнал",
            "Здесь видно, что делает студия. Красные строки — ошибки, зелёные — готово.<br>"
            "«Стоп» прерывает команду, «Очистить» — чистит лог.",
            lambda st: st.log,
            _go_tab(0),
            mascot="m_sleep",
        ),
        Step(
            "Готово!",
            "Коротко: <b>Быстрая установка</b> → запустить игру → <b>Shift+T</b>.<br>"
            "Нужна тонкая настройка — добавь игру в список и жми «Применить в игре».<br><br>"
            "Тур можно повторить кнопкой <b>Тур</b>.",
            lambda st: st.b_tour,
            mascot="m_party",
        ),
    ]


class TourOverlay(QWidget):
    """Затемнение с подсветкой + карточка шага. Ест все клики, пока открыт."""

    PAD = 6

    def __init__(self, studio, icon_dir, accent, on_finish=None):
        super().__init__(studio)
        self.st = studio
        self.icon_dir = icon_dir
        self.accent = QColor(accent)
        self.on_finish = on_finish
        self.steps = steps()
        self.i = 0
        self.hole = None
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, False)
        self._build_card()
        studio.installEventFilter(self)
        self.setGeometry(studio.rect())

    # ---------------------------------------------------------- карточка
    def _build_card(self):
        c = self.card = QFrame(self)
        c.setObjectName("tourCard")
        c.setStyleSheet(
            f"#tourCard{{background:{TOK['bg_card']};border:1px solid {self.accent.name()};border-radius:16px;}}"
            "#tourCard QLabel{background:transparent;}"
            f"#tourTitle{{font-size:13pt;font-weight:800;color:{TOK['text_bright']};}}"
            f"#tourText{{color:{TOK['text_dim']};font-size:10.5pt;}}"
            f"#tourCount{{color:{TOK['text_hint']};font-size:9pt;}}"
        )
        c.setFixedWidth(430)
        v = QVBoxLayout(c)
        v.setContentsMargins(18, 16, 18, 14)
        v.setSpacing(10)
        top = QHBoxLayout()
        top.setSpacing(14)
        self.pic = QLabel()
        self.pic.setFixedSize(76, 76)
        top.addWidget(self.pic, 0, Qt.AlignmentFlag.AlignTop)
        tv = QVBoxLayout()
        tv.setSpacing(6)
        self.lb_title = QLabel(objectName="tourTitle")
        self.lb_title.setWordWrap(True)
        self.lb_text = QLabel(objectName="tourText")
        self.lb_text.setWordWrap(True)
        self.lb_text.setTextFormat(Qt.TextFormat.RichText)
        tv.addWidget(self.lb_title)
        tv.addWidget(self.lb_text)
        top.addLayout(tv, 1)
        v.addLayout(top)
        row = QHBoxLayout()
        self.lb_count = QLabel(objectName="tourCount")
        row.addWidget(self.lb_count)
        row.addStretch(1)
        self.b_skip = QPushButton("Закрыть")
        self.b_back = QPushButton("Назад")
        self.b_next = QPushButton("Далее")
        self.b_next.setObjectName("primary")
        for b in (self.b_skip, self.b_back, self.b_next):
            b.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            row.addWidget(b)
        self.b_skip.clicked.connect(self.finish)
        self.b_back.clicked.connect(lambda: self.go(self.i - 1))
        self.b_next.clicked.connect(lambda: self.go(self.i + 1))
        v.addLayout(row)

    def _mascot(self, name):
        p = os.path.join(self.icon_dir, name + ".png")
        if os.path.exists(p):
            self.pic.setPixmap(
                QPixmap(p).scaled(
                    76,
                    76,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
        else:
            self.pic.clear()

    # ---------------------------------------------------------- ход тура
    def start(self):
        self.setGeometry(self.st.rect())
        self.show()
        self.raise_()
        self.setFocus()
        self.go(0)

    def go(self, i):
        if i >= len(self.steps):
            self.finish()
            return
        self.i = max(0, i)
        s = self.steps[self.i]
        if s.before:
            try:
                s.before(self.st)
            except Exception:
                pass
        self.lb_title.setText(s.title)
        self.lb_text.setText(s.text)
        self._mascot(s.mascot)
        self.lb_count.setText(f"{self.i + 1} из {len(self.steps)}")
        self.b_back.setEnabled(self.i > 0)
        self.b_next.setText("Готово" if self.i == len(self.steps) - 1 else "Далее")
        self._place()

    def finish(self):
        if getattr(self.st, "_tour", None) is self:
            self.st._tour = None
        self.st.removeEventFilter(self)
        self.hide()
        self.deleteLater()
        if self.on_finish:
            self.on_finish()

    # ---------------------------------------------------------- геометрия
    def _target_rect(self):
        s = self.steps[self.i]
        if s.target is None:
            return None
        try:
            t = s.target(self.st)
        except Exception:
            return None
        if t is None:
            return None
        w, r = t if isinstance(t, tuple) else (t, None)
        if w is None or not w.isVisible():
            return None
        r = r if r is not None else w.rect()
        top_left = w.mapTo(self.st, r.topLeft())
        return QRect(top_left, r.size()).adjusted(-self.PAD, -self.PAD, self.PAD, self.PAD)

    def _place(self):
        self.hole = self._target_rect()
        self.card.adjustSize()
        cw, ch = self.card.width(), self.card.sizeHint().height()
        W, H = self.width(), self.height()
        m = 14
        if self.hole is None:
            x, y = (W - cw) // 2, (H - ch) // 2
        else:
            h = self.hole
            if h.bottom() + m + ch <= H - m:  # снизу
                x, y = h.center().x() - cw // 2, h.bottom() + m
            elif h.top() - m - ch >= m:  # сверху
                x, y = h.center().x() - cw // 2, h.top() - m - ch
            elif h.right() + m + cw <= W - m:  # справа
                x, y = h.right() + m, h.center().y() - ch // 2
            else:  # слева / поверх
                x, y = h.left() - m - cw, h.center().y() - ch // 2
            x = max(m, min(x, W - cw - m))
            y = max(m, min(y, H - ch - m))
        self.card.setGeometry(x, y, cw, ch)
        self.card.raise_()
        self.update()

    def eventFilter(self, obj, ev):
        if obj is self.st and ev.type() == QEvent.Type.Resize:
            self.setGeometry(self.st.rect())
            self._place()
        return False

    # ---------------------------------------------------------- рисование/ввод
    def paintEvent(self, _e):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        path = QPainterPath()
        path.addRect(QRectF(self.rect()))
        if self.hole is not None:
            hole = QPainterPath()
            hole.addRoundedRect(QRectF(self.hole), 12, 12)
            path = path.subtracted(hole)
        p.fillPath(path, QColor(5, 7, 11, 200))
        if self.hole is not None:
            pen = QPen(self.accent, 2)
            p.setPen(pen)
            p.drawRoundedRect(QRectF(self.hole), 12, 12)
        p.end()

    def mousePressEvent(self, e):
        e.accept()  # клики под затемнением в студию не проходят

    def keyPressEvent(self, e):
        k = e.key()
        if k == Qt.Key.Key_Escape:
            self.finish()
        elif k in (
            Qt.Key.Key_Right,
            Qt.Key.Key_Return,
            Qt.Key.Key_Enter,
            Qt.Key.Key_Space,
        ):
            self.go(self.i + 1)
        elif k == Qt.Key.Key_Left:
            self.go(self.i - 1)
        else:
            e.accept()


def start_tour(studio, icon_dir, accent, on_finish=None):
    """Открыть тур поверх окна студии (повторный вызов не плодит копии)."""
    old = getattr(studio, "_tour", None)
    if old is not None:
        old.finish()
    studio._tour = TourOverlay(studio, icon_dir, accent, on_finish)
    studio._tour.start()
    return studio._tour
