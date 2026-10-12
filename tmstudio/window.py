"""Главное окно студии: список игр, вкладки карточки, лог и очередь команд tm.py.

Команды пайплайна (collect / curate / gen / deploy / verify / uninstall) идут отдельным
процессом `python tm.py <команда> N` через QProcess — окно не замирает, вывод — в логе.
"""

import hashlib, json, os, sys, re, html, traceback

from PyQt6.QtCore import Qt, QEvent, QProcess, QProcessEnvironment, QSettings, QSize, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
    QDialog,
    QFrame,
    QMenu,
    QStackedWidget,
    QToolButton,
    QPushButton,
    QApplication,
    QMainWindow,
    QWidget,
    QListWidget,
    QListWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QSplitter,
    QMessageBox,
    QFileDialog,
    QInputDialog,
)

from tmkit import games  # логика (ROOTS, launcher, python_exe)
from tmkit import manifest  # чтение/запись games_data.py
from tmkit import validate  # офлайн-проверка данных
from tmkit import engines  # авто-определение движка -> адаптивные вкладки
from tmkit import analysis  # разбор строк кандидатов -> пары для таблицы статов
from tmkit import deploy as tmdeploy  # статус установки: нет / устарело / актуально
from tmkit import generate
from tmkit.paths import CAND_DIR, FROZEN, GAMES_DATA_PATH, ana_dir
from tmkit import naming  # понятные имена переменных (словарь — из движка)

from tmstudio import ROOT, tour
from tmstudio.tokens import TOK
from tmstudio.theme import (
    ACCENT, ENGINE_BADGE, ICON_DIR, ICON_PATH, QSS,
    ibtn, icon, short_title,
)
from tmstudio.tabs import OverviewTab, TableTab, CandidatesTab
from tmstudio.widgets import GAME_ROLE, ApplyPreview, GameDelegate, LogPanel, NavRail, WelcomePage

TM_PY = os.path.join(ROOT, "tm.py")


# ============================================================ окно-контроллер
class Studio(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Test Menu Studio")
        if os.path.exists(ICON_PATH):
            self.setWindowIcon(QIcon(ICON_PATH))
        self.resize(1180, 760)
        self.settings = QSettings("TestMenuMoon", "Studio")
        if not self.settings.allKeys():  # прежнее имя проекта: перенести настройки
            old = QSettings("RenpyTestMenu", "Studio")
            for k in old.allKeys():
                self.settings.setValue(k, old.value(k))
        geo = self.settings.value("geometry")
        if geo is not None:
            self.restoreGeometry(geo)

        self.games, self.G, self.accent = manifest.load_games()
        self.cur = None  # текущий индекс игры
        self.cur_engine = None  # движок текущей игры (для scan/deploy-маршрутизации)
        self._dirty_ids = set()  # игры с несохранёнными правками (раньше флаг был один на окно)

        # --- очередь команд для QProcess ---
        self.proc = QProcess(self)
        env = QProcessEnvironment.systemEnvironment()
        env.insert("PYTHONIOENCODING", "utf-8")
        env.insert("PYTHONUTF8", "1")
        self.proc.setProcessEnvironment(env)
        self.proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self.proc.readyReadStandardOutput.connect(self._on_output)
        self.proc.finished.connect(self._on_proc_finished)
        self.proc.errorOccurred.connect(self._on_proc_error)
        self.queue = []
        self._out_buf = ""  # неполный «хвост» stdout между чтениями

        self._build_ui()
        QShortcut(QKeySequence.StandardKey.Save, self).activated.connect(
            self._save_manifest
        )
        # список игр правят и руками (games_data.py): F5 — перечитать, а при возврате в окно
        # студия сама замечает изменения на диске (отдельной кнопки больше нет)
        QShortcut(QKeySequence("F5"), self).activated.connect(self._reload_from_disk)
        self._manifest_mtime = self._manifest_mtime_now()
        self._reload_list()
        if self.games:
            self.list.setCurrentRow(0)
        if self.settings.value("tour_done", False, type=bool) is not True:
            QTimer.singleShot(500, self.start_tour)
        QTimer.singleShot(1500, self._check_library)

    def start_tour(self):
        self.show_page(0)

        def done():
            self.settings.setValue("tour_done", True)

        tour.start_tour(self, ICON_DIR, ACCENT, on_finish=done)

    @property
    def _dirty(self):
        return bool(self._dirty_ids)

    def _clear_dirty(self):
        self._dirty_ids.clear()
        self.setWindowTitle("Test Menu Studio")

    # ------------------------------------------------------------ вёрстка
    # Разделы (полоса слева): 0 Игры, 1 Библиотека, 2 Пульт, 3 Сохранения.
    # Вкладки игры — шаги: 0 Основное, 1 Найти переменные, 2 Статы, 3 Выдача.
    TAB_MAIN, TAB_FIND, TAB_STATS, TAB_GIVE = range(4)

    def _build_ui(self):
        wrap = QWidget()
        outer = QHBoxLayout(wrap)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        self.rail = NavRail(
            [
                ("Игры", "house", "Мои игры и настройка меню"),
                ("Библиотека", "load", "Все игры в папке: поставить или обновить меню пачкой"),
                ("Пульт", "remote", "Управлять запущенной игрой из студии (в меню игры включи «Пульт в студии»)"),
                ("Сейвы", "save", "Редактор сохранений выбранной игры"),
            ],
            bottom=[("Тур", "question", "Пошаговый тур по студии", self.start_tour)],
        )
        self.b_tour = self.rail.extra[0]
        self.rail.changed.connect(self.show_page)
        outer.addWidget(self.rail)

        body = QWidget()
        bl = QVBoxLayout(body)
        bl.setContentsMargins(14, 12, 14, 10)
        bl.setSpacing(0)
        self.pages = QStackedWidget()
        self.pages.addWidget(self._build_games_page())
        self.pages.addWidget(self._page_shell("Библиотека", "Укажи папку с играми: студия найдёт игры, покажет "
                                              "движок и состояние меню и поставит или обновит меню пачкой."))
        self.pages.addWidget(self._page_shell("Пульт", "Значения, заморозки, темп и шаг кадра запущенной игры. "
                                              "В меню игры включи «Пульт в студии»."))
        self.pages.addWidget(self._page_shell("Сохранения", "Сейвы выбранной игры: Ren'Py, RPG Maker, Unity "
                                              "(PlayerPrefs, JSON), Godot. Снимки и сравнение."))
        bl.addWidget(self.pages, 1)
        self.logp = LogPanel(self._stop_proc)
        self.log = self.logp.log
        self.b_stop = self.logp.b_stop
        bl.addWidget(self.logp)
        outer.addWidget(body, 1)
        self.setCentralWidget(wrap)

    def _page_shell(self, title, sub):
        """Страница раздела: заголовок + пояснение; содержимое создаётся при первом показе."""
        w = QWidget()
        v = QVBoxLayout(w)
        v.setContentsMargins(4, 2, 4, 8)
        v.setSpacing(4)
        v.addWidget(QLabel(title, objectName="h1"))
        s = QLabel(sub, objectName="dim")
        s.setWordWrap(True)
        v.addWidget(s)
        v.addSpacing(8)
        w.body = v
        w.content = None
        return w

    def show_page(self, i):
        """Показать раздел; Библиотека, Пульт и Сохранения собираются при первом показе."""
        self.rail.select(i)
        page = self.pages.widget(i)
        if i == 1:
            if page.content is None:
                from tmstudio.library import LibraryDialog

                page.content = LibraryDialog(page, self.games, self._add_to_manifest, self._library_changed)
                page.content.setWindowFlags(Qt.WindowType.Widget)
                page.body.addWidget(page.content, 1)
            page.content.games = self.games  # после перечитывания списка — новый словарь
        elif i == 2 and page.content is None:
            from tmstudio.remote import RemoteDialog

            page.content = RemoteDialog(page)
            page.content.setWindowFlags(Qt.WindowType.Widget)
            page.body.addWidget(page.content, 1)
        elif i == 3:
            from tmstudio import save_editor

            if page.content is None:
                page.content = save_editor.SaveEditor(page)
                page.content.setWindowFlags(Qt.WindowType.Widget)
                page.body.addWidget(page.content, 1)
                page.content._root = None
            root = self.games[self.cur].get("root", "") if self.cur is not None else ""
            if root and root != page.content._root:
                eng = engines.detect_engine(root)
                page.content._root = root
                page.content._load_game(root, eng.key if eng else None)
        self.pages.setCurrentIndex(i)
        if getattr(page, "content", None) is not None:
            page.content.show()

    def _build_games_page(self):
        split = QSplitter(Qt.Orientation.Horizontal)

        # ---- левая колонка: мои игры ----
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 2, 6, 0)
        lv.setSpacing(8)
        head = QHBoxLayout()
        head.addWidget(QLabel("Мои игры", objectName="h1"))
        head.addStretch(1)
        b_add = ibtn("", "plus", "Добавить игру в список (выбрать папку игры)", px=22)
        b_add.setObjectName("iconbtn")
        b_add.clicked.connect(self._add_game)
        self.b_add_game = b_add
        head.addWidget(b_add)
        lv.addLayout(head)
        # плашка «меню устарело в N играх» — проверка библиотеки при запуске (_check_library)
        self.update_bar = QFrame(objectName="warnbar")
        ub = QHBoxLayout(self.update_bar)
        ub.setContentsMargins(10, 6, 6, 6)
        self.update_lbl = QLabel("")
        self.update_lbl.setWordWrap(True)
        ub.addWidget(self.update_lbl, 1)
        self.b_update = QPushButton("Обновить")
        self.b_update.clicked.connect(self._update_stale)
        b_hide = ibtn("", "close", "Скрыть до следующего запуска", px=16)
        b_hide.setObjectName("iconbtn")
        b_hide.clicked.connect(self.update_bar.hide)
        ub.addWidget(self.b_update)
        ub.addWidget(b_hide)
        self.update_bar.hide()
        lv.addWidget(self.update_bar)
        self.list_filter = QLineEdit()
        self.list_filter.setPlaceholderText("Поиск игры")
        self.list_filter.setClearButtonEnabled(True)
        self.list_filter.textChanged.connect(self._filter_list)
        lv.addWidget(self.list_filter)
        self.list = QListWidget(objectName="games")
        self.list.setItemDelegate(GameDelegate(self.list))
        self.list.setMouseTracking(True)
        self.list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list.currentRowChanged.connect(self._on_select)
        lv.addWidget(self.list, 1)
        self.b_quick = ibtn("Быстрая установка…", "download")
        self.b_quick.setToolTip(
            "Поставить меню в любую игру без добавления в список.\n"
            "Статы меню найдёт само (режим «авто»), подсказки к выборам и сканер тоже работают."
        )
        self.b_quick.clicked.connect(self._quick_install)
        lv.addWidget(self.b_quick)
        gb = QHBoxLayout()
        self.b_all_dep = ibtn("Применить во всех", "upload",
                              "Сохранить правки и поставить или обновить меню во всех играх списка")
        self.b_all_dep.clicked.connect(self._deploy_all)
        self.b_all_ver = ibtn("Проверить всё", "checklist", "Проверка (lint) всех игр Ren'Py из списка")
        self.b_all_ver.clicked.connect(lambda: self._enqueue("verify"))
        gb.addWidget(self.b_all_dep, 1)
        gb.addWidget(self.b_all_ver, 1)
        lv.addLayout(gb)
        split.addWidget(left)

        # ---- правая часть: игра или приветствие ----
        self.right = QStackedWidget()
        self.welcome = WelcomePage(
            ICON_PATH if os.path.exists(ICON_PATH) else None,
            on_folder=self._welcome_folder,
            on_add=self._add_game,
            on_quick=self._quick_install,
            on_tour=self.start_tour,
        )
        self.right.addWidget(self._build_game_panel())
        self.right.addWidget(self.welcome)
        split.addWidget(self.right)
        split.setStretchFactor(0, 0)
        split.setStretchFactor(1, 1)
        split.setSizes([320, 880])
        return split

    def _build_game_panel(self):
        panel = QWidget()
        v = QVBoxLayout(panel)
        v.setContentsMargins(8, 2, 0, 0)
        v.setSpacing(10)
        # шапка игры: название, состояние, одна главная кнопка + «…»
        hdr = QHBoxLayout()
        hdr.setSpacing(8)
        tv = QVBoxLayout()
        tv.setSpacing(0)
        self.g_title = QLabel("", objectName="h1")
        self.g_sub = QLabel("", objectName="dim")
        tv.addWidget(self.g_title)
        tv.addWidget(self.g_sub)
        hdr.addLayout(tv, 1)
        self.b_run = ibtn("Запустить", "play", "Запустить игру, чтобы посмотреть меню")
        self.b_run.clicked.connect(self._launch_current)
        self.b_primary = ibtn("Применить в игре", "upload")
        self.b_primary.setObjectName("primary")
        self.b_primary.clicked.connect(self._apply_current)
        self.b_more = QToolButton(objectName="more")
        self.b_more.setText("•••")
        self.b_more.setToolTip("Ещё действия")
        self.b_more.setPopupMode(QToolButton.ToolButtonPopupMode.InstantPopup)
        m = QMenu(self.b_more)
        self.act_check = m.addAction(icon("checklist"), "Проверить", self._check_current)
        m.addAction(icon("load"), "Открыть папку игры", self._open_folder)
        m.addAction(icon("save"), "Сохранения игры", lambda: self.show_page(3))
        m.addAction("Сохранить без установки  (Ctrl+S)", self._save_manifest)
        m.addSeparator()
        self.act_uninstall = m.addAction(icon("trash"), "Удалить меню из игры", self._uninstall)
        m.addAction("Убрать из списка студии", self._remove_game)
        self.b_more.setMenu(m)
        for b in (self.b_run, self.b_primary, self.b_more):
            hdr.addWidget(b, 0, Qt.AlignmentFlag.AlignVCenter)
        v.addLayout(hdr)

        self.overview = OverviewTab(on_dirty=self._mark_dirty, default_accent=self.accent)
        self.stats_tab = TableTab(
            ["Название", "Где лежит (пусто — заголовок группы)", "мин", "макс"],
            "где лежит значение в игре, например mc.money",
            self._mark_dirty,
        )
        self.actions_tab = TableTab(
            ["Название", "Код (пусто — заголовок группы)"],
            "код выполняется внутри игры, например mc.money += 1000",
            self._mark_dirty,
        )
        self.cand_tab = CandidatesTab(
            f"Найденные переменные игры (файл {CAND_DIR}/game_N.txt). "
            "После «//» — понятное имя, «догадка» — если только по названию",
            on_collect=lambda: self._enqueue_current("collect"),
            on_curate=self._run_curate,
            on_refresh=self._load_cand,
            on_full=self._full_pipeline,
            on_add_stats=self._add_stats_from_candidates,
        )
        self.tabs = QTabWidget()
        self.tabs.setIconSize(QSize(18, 18))
        self.tabs.addTab(self.overview, icon("house"), "1  Основное")
        self.tabs.addTab(self.cand_tab, icon("scanner"), "2  Найти переменные")
        self.tabs.addTab(self.stats_tab, icon("stats"), "3  Статы")
        self.tabs.addTab(self.actions_tab, icon("actions"), "4  Выдача")
        v.addWidget(self.tabs, 1)
        return panel

    def _welcome_folder(self):
        self.show_page(1)
        page = self.pages.widget(1)
        if page.content is not None:
            page.content._pick()

    def _set_header(self, i):
        """Шапка игры: название, движок и состояние; текст главной кнопки — по ситуации."""
        g = self.games[i]
        eng = self.cur_engine
        st = self._status(i, eng)
        name = ENGINE_BADGE.get(eng.key, eng.title) if eng else "движок не распознан"
        state = {"ok": "меню стоит, версия свежая", "stale": "меню устарело",
                 "none": "меню не установлено"}[st]
        if i in self._dirty_ids:
            state += ", есть несохранённые правки"
        self.g_title.setText(short_title(g.get("title", "")))
        self.g_sub.setText(f"{name}, {state}")
        self.b_primary.setText({"none": "Установить меню", "stale": "Обновить меню"}.get(st, "Применить в игре"))
        self.b_primary.setToolTip("Сохранить правки и поставить или обновить меню в игре")

    # ------------------------------------------------------------ модель/список
    def _reload_list(self):
        self.list.blockSignals(True)
        self.list.clear()
        for i in sorted(self.games):
            g = self.games[i]
            root = g.get("root", "")
            eng = engines.detect_engine(root)
            st = self._status(i, eng)
            n_stat = len([s for s in g.get("stats", []) if s[1]])
            n_act = len([a for a in g.get("actions", []) if a[1]])
            counts = []
            if n_stat:
                counts.append(f"статы: {n_stat}")
            if n_act:
                counts.append(f"выдача: {n_act}")
            title = short_title(g.get("title", ""))
            ename = ENGINE_BADGE.get(eng.key, eng.title) if eng else "движок не распознан"
            it = QListWidgetItem(f"{title} {ename}")  # текст — для поиска, рисует GameDelegate
            it.setData(GAME_ROLE, {
                "title": title, "engine": eng.key if eng else None, "engine_name": ename,
                "counts": ", ".join(counts), "status": st, "dirty": i in self._dirty_ids,
            })
            it.setToolTip(
                f"game_{i}  {root}\n"
                + {"ok": "Меню стоит, версия свежая",
                   "stale": "Меню устарело — «Обновить меню»",
                   "none": "Меню не установлено"}[st]
            )
            it.setData(Qt.ItemDataRole.UserRole, i)
            self.list.addItem(it)
            if i == self.cur:  # clear() сбрасывает выделение — вернуть
                self.list.setCurrentItem(it)  # (сигналы заглушены: UI игры уже загружен)
        self.list.blockSignals(False)
        self.right.setCurrentIndex(0 if self.games else 1)
        self._filter_list(self.list_filter.text())

    def _filter_list(self, text):
        q = text.strip().lower()
        for row in range(self.list.count()):
            it = self.list.item(row)
            it.setHidden(bool(q) and q not in it.text().lower())

    def _on_select(self, row):
        if row < 0:
            return
        # сохранить правки текущей игры в память перед переключением
        if self.cur is not None:
            self._flush_ui_to_model()
        i = self.list.item(row).data(Qt.ItemDataRole.UserRole)
        self.cur = i
        self._load_game_to_ui(i)

    def _load_game_to_ui(self, i):
        g = self.games[i]
        # по пути, а не по индексу: games.GAMES — снимок на импорт и не знает игр,
        # добавленных в этом сеансе (KeyError ронял студию сразу после «+ игра»)
        root = g.get("root", "")
        lnch = games.launcher_of(root)
        py = games.python_exe_of(root)
        launcher_text = (
            f"{os.path.basename(lnch) if lnch else '—'}   |   "
            f"{os.path.basename(os.path.dirname(py)) if py else 'нет python'}"
        )
        eng = engines.detect_engine(g.get("root", ""))
        self.cur_engine = eng
        eng_text = eng.title if eng else "не распознан (по умолчанию Ren'Py)"
        self.overview.load(
            g.get("title", ""),
            g.get("status", ""),
            g.get("root", "—"),
            launcher_text,
            self._status_text(i),
            eng_text,
            g.get("accent", ""),
        )
        self._apply_engine_tabs(eng)
        renpy_mode = eng is None or eng.key == "renpy"
        self.act_check.setToolTip(
            "Проверить данные меню и прогнать проверку самой игры (lint Ren'Py)"
            if renpy_mode else "Проверить данные меню: код выдачи, повторы, группы"
        )
        self._set_header(i)
        self.cand_tab.set_mode(
            renpy_mode,
            None
            if renpy_mode
            else f"{eng.title}: имена/значения читаются прямо из данных игры",
        )
        self.stats_tab.fill(g.get("stats", []))
        self.actions_tab.fill(g.get("actions", []))
        self._load_cand()

    def _apply_engine_tabs(self, eng):
        """Включить только вкладки, релевантные движку (None -> Ren'Py-манифест, всё вкл)."""
        gen = eng.supports("generate") if eng else True  # статы/действия из манифеста
        scan = eng.supports("scan") if eng else True  # поиск кандидатов
        self.tabs.setTabEnabled(self.TAB_STATS, gen)
        self.tabs.setTabEnabled(self.TAB_GIVE, gen)
        self.tabs.setTabEnabled(self.TAB_FIND, scan)
        if not self.tabs.isTabEnabled(self.tabs.currentIndex()):
            self.tabs.setCurrentIndex(self.TAB_MAIN)

    def _flush_ui_to_model(self):
        if self.cur is None:
            return
        g = self.games[self.cur]
        title, status, accent = self.overview.read()
        if accent and QColor(accent).isValid():
            accent = QColor(
                accent
            ).name()  # «red», #abc -> #rrggbb (Ren'Py имён цветов не знает)
        g["title"] = title
        g["status"] = status
        g["accent"] = accent
        g["stats"] = self.stats_tab.read()
        g["actions"] = self.actions_tab.read()

    def _is_installed(self, i):
        """Установлено ли меню — движок-осведомлённо (Ren'Py: файл движка; Twine/RPGMaker: маркер)."""
        root = self.games[i].get("root", "")
        return self._installed_with(engines.detect_engine(root), root)

    def _status(self, i, eng=False):
        """'none' | 'stale' | 'ok'. stale = в игре лежит не та версия движка/данных, что
        сейчас в проекте и манифесте (после правки движка или статов без раскладки)."""
        g = self.games[i]
        root = g.get("root", "")
        if eng is False:
            eng = engines.detect_engine(root)
        try:
            if eng is None or eng.key == "renpy":
                return tmdeploy.status(root, generate.render_game(i, g, self.accent))
            if not self._installed_with(eng, root):
                return "none"
            return "ok" if (eng.current is None or eng.current(root)) else "stale"
        except Exception:
            return "none"

    def _status_text(self, i):
        return {
            "ok": "стоит, свежая версия",
            "stale": "устарело — нажми «Обновить меню»",
            "none": "не стоит — нажми «Установить меню»",
        }[self._status(i)]

    def _installed_with(self, eng, root):
        """То же, но по уже определённому движку (без повторного detect)."""
        if eng is not None and eng.installed is not None:
            try:
                return eng.installed(root)
            except Exception:
                return False
        return os.path.exists(os.path.join(root, "zzz_testmenu_engine.rpy"))

    def _run_engine_action(self, i, fn, verb):
        """Синхронно выполнить действие движка (deploy/uninstall) над одной игрой по пути."""
        root = self.games[i].get("root", "")
        try:
            self._log_line(f"$ {verb} game_{i}: {fn(root)}")
        except Exception as e:
            self._log_line(f"! {verb} game_{i}: {e}")
        self._reload_list()
        if i == self.cur:
            self.overview.set_installed(self._status_text(i))
            self._set_header(i)

    # ------------------------------------------------------------ действия
    def _mark_dirty(self, *_):
        if self.cur is None:
            return
        self._dirty_ids.add(self.cur)
        self.setWindowTitle(
            f"Test Menu Studio  •  несохранённые правки: {len(self._dirty_ids)}"
        )
        for row in range(self.list.count()):
            it = self.list.item(row)
            if it.data(Qt.ItemDataRole.UserRole) == self.cur:
                d = dict(it.data(GAME_ROLE) or {})
                if not d.get("dirty"):
                    d["dirty"] = True
                    it.setData(GAME_ROLE, d)
                break
        self._set_header(self.cur)

    def _save_manifest(self):
        self._flush_ui_to_model()
        manifest.save_games(self.games, self.G, self.accent)
        self._manifest_mtime = self._manifest_mtime_now()
        self._clear_dirty()
        self._log_line("$ список игр сохранён (tmkit/games_data.py)")
        self._reload_list()
        if self.cur is not None:
            self.overview.set_installed(self._status_text(self.cur))
            self._set_header(self.cur)

    def _save_and_deploy(self):
        if self.cur is None:
            return
        self._save_manifest()
        eng = self.cur_engine
        if eng is not None and eng.key != "renpy" and eng.deploy is not None:
            self._run_engine_action(
                self.cur, eng.deploy, "deploy"
            )  # синхронно, без QProcess
        else:
            self._enqueue("gen", str(self.cur))
            self._enqueue("deploy", str(self.cur))

    # ---- «Применить в игре»: сначала показать, что изменится ----
    def _applied_key(self, root):
        return "applied/" + hashlib.md5(os.path.normcase(os.path.abspath(root)).encode("utf-8")).hexdigest()

    @staticmethod
    def _apply_snapshot(g):
        """То, что меню получит из студии: названия статов и выдачи, название и цвет."""
        def rows(key):
            return {r[0]: str(r[1]) for r in g.get(key, []) if len(r) > 1 and r[1]}
        return {"stats": rows("stats"), "actions": rows("actions"),
                "title": g.get("title", ""), "accent": g.get("accent", "")}

    def _apply_plan(self, i):
        g = self.games[i]
        eng = self.cur_engine
        st = self._status(i, eng)
        lines = []
        if st == "none":
            lines.append(("+", "Меню будет установлено в игру", ""))
        elif st == "stale":
            lines.append(("~", "Меню обновится до текущей версии", ""))
        if eng is None or eng.supports("generate"):
            cur = self._apply_snapshot(g)
            raw = self.settings.value(self._applied_key(g.get("root", "")), "")
            prev = json.loads(raw) if raw else None
            if prev is None:
                if st == "none" and (cur["stats"] or cur["actions"]):
                    lines.append(("+", f"Статов: {len(cur['stats'])}, выдачи: {len(cur['actions'])}", ""))
            else:
                for key, word in (("stats", "Стат"), ("actions", "Выдача")):
                    a, b = prev.get(key, {}), cur[key]
                    for k, val in b.items():
                        if k not in a:
                            lines.append(("+", f"{word} «{k}»", val[:40]))
                        elif a[k] != val:
                            lines.append(("~", f"{word} «{k}»", val[:40]))
                    lines += [("-", f"{word} «{k}»", "") for k in a if k not in b]
                if prev.get("title") != cur["title"]:
                    lines.append(("~", "Название в меню", short_title(cur["title"])))
                if prev.get("accent", "") != cur["accent"]:
                    lines.append(("~", "Цвет меню", cur["accent"] or "как у всех игр"))
        return lines

    def _apply_current(self):
        if self.cur is None:
            return
        self._flush_ui_to_model()
        i = self.cur
        lines = self._apply_plan(i)
        if lines and self.settings.value("confirm_apply", True, type=bool):
            dlg = ApplyPreview(self, f"Применить в «{short_title(self.games[i].get('title', ''))}»", lines)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            if dlg.ask.isChecked():
                self.settings.setValue("confirm_apply", False)
        for sign, text, detail in lines:
            self._log_line(f"  {sign} {text}" + (f"  ({detail})" if detail else ""))
        self._save_and_deploy()
        g = self.games[i]
        self.settings.setValue(self._applied_key(g.get("root", "")),
                               json.dumps(self._apply_snapshot(g), ensure_ascii=False))

    def _check_current(self):
        """Одна проверка: данные меню без запуска игры, у Ren'Py ещё и lint самой игры."""
        self._validate_current()
        if self.cur_engine is None or self.cur_engine.key == "renpy":
            self._enqueue_current("verify")

    def _deploy_all(self):
        if self._dirty:
            self._save_manifest()
        # Ren'Py — батч по индексам через CLI; не-Ren'Py — синхронный engine.deploy по пути
        renpy_ids = []
        for i in sorted(self.games):
            eng = engines.detect_engine(self.games[i].get("root", ""))
            if eng is not None and eng.key != "renpy" and eng.deploy is not None:
                self._run_engine_action(i, eng.deploy, "deploy")
            else:
                renpy_ids.append(str(i))
        if renpy_ids:
            self._enqueue("gen", *renpy_ids)
            self._enqueue("deploy", *renpy_ids)

    def _uninstall(self):
        if self.cur is None:
            return
        if (
            QMessageBox.question(
                self,
                "Удалить меню",
                f"Удалить меню из «{short_title(self.games[self.cur].get('title', ''))}»?\n\n"
                "Файлы самой игры не трогаются.",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        eng = self.cur_engine
        if eng is not None and eng.key != "renpy" and eng.uninstall is not None:
            self._run_engine_action(self.cur, eng.uninstall, "uninstall")
        else:
            self._enqueue("uninstall", str(self.cur))

    def _open_folder(self):
        if self.cur is None:
            return
        path = self.games[self.cur]["root"].replace("/", os.sep)
        try:
            os.startfile(path)
        except Exception as e:
            self._log_line(f"! не удалось открыть {path}: {e}")

    def _launch_current(self):
        """Запустить игру для проверки меню (отдельным процессом, не мешая очереди)."""
        if self.cur is None:
            return
        i = self.cur
        root = self.games[i].get("root", "")
        key = self.cur_engine.key if self.cur_engine else "renpy"
        try:
            program, args, cwd = self._launch_command(i, key, root)
        except Exception as e:
            self._log_line(f"! запуск game_{i}: {e}")
            return
        if not program:
            self._log_line(f"! запуск game_{i}: не нашёл, чем запустить ({key})")
            return
        if args is None:  # exe/html — через ассоциацию ОС
            try:
                # рабочая папка — папка игры: иначе игра стартовала в папке студии, и те,
                # что читают ресурсы по относительным путям, падали или не находили сейвы
                os.startfile(program, cwd=os.path.dirname(os.path.abspath(program)))
                self._log_line(f"$ запуск game_{i}: {program}")
            except Exception as e:
                self._log_line(f"! запуск game_{i}: {e}")
        else:  # интерпретатор + скрипт, detached
            ok = QProcess.startDetached(program, args, cwd or "")
            self._log_line(
                f"$ запуск game_{i}: {program} {' '.join(args)}"
                if ok
                else f"! запуск game_{i}: не удалось стартовать {program}"
            )

    def _launch_command(self, i, key, root):
        """(program, args|None, cwd|None). args=None -> открыть program как файл (os.startfile)."""
        if key == "renpy":
            lnch = games.launcher_of(root)
            if lnch:
                exe = lnch[:-3] + ".exe"
                if os.path.exists(exe):
                    return (exe, None, None)  # родной .exe игры
                py = games.python_exe_of(root)
                if py:
                    return (py, [lnch], games.basedir_of(root))
            exe = games.pick_exe(games.basedir_of(root))
            return (exe, None, None) if exe else (None, None, None)
        # не-Ren'Py: nw.js .exe рядом, иначе — открыть html в браузере/приложении
        # (pick_exe пропускает notification_helper, UnityCrashHandler и т.п.)
        exe = games.pick_exe(root)
        if exe:
            return (exe, None, None)
        try:
            return (engines._load_inject(key).target_html(root), None, None)
        except Exception:
            return (None, None, None)

    def _validate_current(self):
        if self.cur is None:
            return
        stats = self.stats_tab.read()
        actions = self.actions_tab.read()
        issues = validate.check_game(stats, actions, self.overview.read()[2])
        if not issues:
            QMessageBox.information(self, "Проверка", "Данные меню в порядке.")
        else:
            QMessageBox.warning(
                self,
                "Проверка",
                "Найдено проблем: %d\n\n%s" % (len(issues), "\n".join(issues)),
            )
        self._log_line(
            "$ проверка данных game_%s: проблем %d" % (self.cur, len(issues))
        )

    def _run_curate(self):
        # не-Ren'Py движок со scan-возможностью: читаем данные игры напрямую (без QProcess)
        eng = self.cur_engine
        if eng is not None and eng.key != "renpy" and eng.scan is not None:
            self._run_engine_scan(eng)
        else:
            self._enqueue_current("curate")

    def _add_stats_from_candidates(self, pairs):
        if self.cur is None:
            return
        if not pairs:
            self._log_line(
                "! в выделенном нет строк-кандидатов (нужны «имя = значение» или «… -> путь»)"
            )
            return
        try:
            chars, names = self._naming_ctx(self.cur)
            pairs = [(naming.label_for(p[0], p[1], chars, names),) + tuple(p[1:]) for p in pairs]
        except Exception as e:
            self._log_line(f"! понятные имена: {e}")
        n = self.stats_tab.add_pairs(pairs)
        self._log_line(
            f"$ в статы game_{self.cur}: добавлено {n}, уже было {len(pairs) - n}"
        )

    def _run_engine_scan(self, eng):
        """Синхронный статический скан движка (RPG Maker и т.п.): пишем отчёт в тот же
        cand-файл, что и Ren'Py, и показываем его во вкладке."""
        if self.cur is None:
            return
        root = self.games[self.cur].get("root", "")
        try:
            text = eng.scan(root)
        except Exception as e:
            self._log_line(f"! scan ({eng.key}) game_{self.cur}: {e}")
            self.cand_tab.set_text(f"Ошибка скана: {e}")
            return
        p = os.path.join(CAND_DIR, f"game_{self.cur}.txt")
        try:
            os.makedirs(CAND_DIR, exist_ok=True)
            with open(p, "w", encoding="utf-8") as f:
                f.write(text)
        except Exception as e:
            self._log_line(f"! не удалось записать {p}: {e}")
        self.cand_tab.set_text(text)
        self._log_line(f"$ scan ({eng.key}) game_{self.cur} -> {p}")

    def _full_pipeline(self):
        if self.cur is None:
            return
        # офлайн-проверка перед деплоем: синтаксис действий блокирует пайплайн
        issues = validate.check_game(
            self.stats_tab.read(), self.actions_tab.read(), self.overview.read()[2]
        )
        syntax = [s for s in issues if "синтаксис" in s]
        if syntax:
            QMessageBox.critical(
                self,
                "Отменено",
                "Синтаксические ошибки в действиях:\n\n" + "\n".join(syntax),
            )
            self._log_line(
                "$ отменено: ошибка в коде выдачи (%d)" % len(syntax)
            )
            return
        if issues:
            QMessageBox.warning(
                self,
                "Проверка данных",
                "Замечания (не блокируют):\n\n" + "\n".join(issues),
            )
        self._save_manifest()
        for script in (
            "collect",
            "curate",
            "gen",
            "deploy",
        ):
            self._enqueue(script, str(self.cur))

    def _naming_ctx(self, i):
        """(персонажи, свои имена) игры i для понятных подписей; персонажи — с кэшем."""
        root = self.games[i].get("root", "")
        cache = self.__dict__.setdefault("_chars_cache", {})
        if root not in cache:
            try:
                cache[root] = naming.characters(root, ana_dir(i))
            except Exception:
                cache[root] = {}
        return cache[root], naming.user_names(root)

    def _load_cand(self):
        if self.cur is None:
            return
        p = os.path.join(CAND_DIR, f"game_{self.cur}.txt")
        if os.path.exists(p):
            try:
                text = open(p, encoding="utf-8", errors="replace").read()
                try:
                    chars, names = self._naming_ctx(self.cur)
                    text = naming.annotate(text, analysis.parse_candidates, chars, names)
                except Exception as e:
                    self._log_line(f"! понятные имена: {e}")
                self.cand_tab.set_text(text)
            except Exception as e:
                self.cand_tab.set_text(f"Ошибка чтения: {e}")
        else:
            eng = self.cur_engine
            if eng is not None and eng.key != "renpy" and eng.scan is not None:
                msg = "Скан ещё не запускался.\nНажми «Сканировать данные»."
            else:
                msg = (
                    "Файла кандидатов ещё нет.\n"
                    "Нажми «1. Распаковать игру», затем «2. Найти переменные»."
                )
            self.cand_tab.set_text(msg, empty=True)

    def _select_index(self, idx):
        """Выделить в списке игру с данным индексом манифеста."""
        for row in range(self.list.count()):
            if self.list.item(row).data(Qt.ItemDataRole.UserRole) == idx:
                self.list.setCurrentRow(row)
                return

    def _commit_structure(self, change):
        """Добавить/убрать игру. На диск уходит ТОЛЬКО это изменение (поверх манифеста
        с диска) — несохранённые правки других игр остаются в памяти и с пометкой.
        Раньше save_games(self.games) молча записывал заодно и их."""
        disk, G, acc = manifest.load_games()
        res = change(disk)
        manifest.save_games(disk, G, acc)
        self._manifest_mtime = self._manifest_mtime_now()
        change(self.games)
        return res

    def _add_to_manifest(self, root, title):
        root = root.replace("\\", "/")
        disk = manifest.load_games()[0]
        idx = manifest.next_index({**disk, **self.games})  # свободен и там, и там
        self._commit_structure(lambda gs: manifest.add_game(gs, root, title=title, index=idx))
        return idx

    # ------------------------------------------------------------ автопроверка библиотеки
    def _check_library(self):
        """Тихо проверить папку библиотеки (из «Библиотеки игр…») и игры манифеста: где меню
        устарело — плашка над списком. Проверка в фоне: статус игр читает файлы с диска."""
        if not self.settings.value("library_autocheck", True, type=bool):
            return
        folder = self.settings.value("library_dir", "") or ""
        self._lib_worker = _LibraryCheck(folder, dict(self.games), self)
        self._lib_worker.done.connect(self._library_checked)
        self._lib_worker.start()

    def _library_checked(self, stale):
        self.stale = stale
        if not stale:
            self.update_bar.hide()
            return
        names = ", ".join(short_title(g.name) for g in stale[:3]) + (" …" if len(stale) > 3 else "")
        self.update_lbl.setText(f"Меню устарело в играх: {len(stale)} ({names})")
        self.update_bar.show()

    def _update_stale(self):
        from PyQt6.QtWidgets import QApplication
        from tmkit import library

        if self._dirty:
            self._save_manifest()
        ok, errors = 0, []
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            for g in getattr(self, "stale", []):
                try:
                    self._log_line(f"$ обновление: {library.install(g)}")
                    ok += 1
                except Exception as e:
                    errors.append(f"{g.name}: {e}")
                    self._log_line(f"! обновление {g.name}: {e}")
        finally:
            QApplication.restoreOverrideCursor()
        self.update_bar.hide()
        self._library_changed()
        self._log_line(f"$ обновлено меню: {ok}" + (f", ошибок: {len(errors)}" if errors else ""))

    def _open_remote(self):
        self.show_page(2)

    def _open_library(self):
        self.show_page(1)

    def _library_changed(self):
        self._reload_list()
        if self.cur is not None:
            self.overview.set_installed(self._status_text(self.cur))
            self._set_header(self.cur)

    def _add_game(self):
        d = QFileDialog.getExistingDirectory(
            self, "Ren'Py — папка game/; Godot, Unity, RPG Maker — папка игры; Twine и HTML5 — папка с .html"
        )
        if not d:
            return
        eng = engines.detect_engine(d)
        if (eng is None or eng.key == "renpy") and os.path.basename(d.rstrip("/\\")).lower() != "game":
            if (
                QMessageBox.question(
                    self,
                    "Проверь папку",
                    f"Папка называется не «game»:\n{d}\n\nВсё равно добавить?",
                )
                != QMessageBox.StandardButton.Yes
            ):
                return
        dup = manifest.find_by_root(self.games, d)
        if dup is not None:
            if (
                QMessageBox.question(
                    self,
                    "Игра уже в списке",
                    f"Эта папка уже добавлена как game_{dup}.\n\nДобавить второй раз?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                != QMessageBox.StandardButton.Yes
            ):
                self._select_index(dup)
                return
        default_title = manifest.default_title(d)  # без «[v0.5]», «-pc» и т.п.
        title, ok = QInputDialog.getText(
            self, "Новая игра", "Заголовок меню:", text=default_title
        )
        if not ok:
            return
        if self.cur is not None:
            self._flush_ui_to_model()
        idx = self._add_to_manifest(d, title.strip() or "TEST MENU")
        self._log_line(f"$ добавлена game_{idx} -> {d}")
        self._reload_list()
        self._select_index(idx)

    def _open_saves(self):
        self.show_page(3)

    def _quick_install(self):
        d = QFileDialog.getExistingDirectory(
            self, "Папка игры: Ren'Py (корень или game/), Godot, Unity, RPG Maker, Twine, HTML5, Unreal"
        )
        if not d:
            return
        try:
            eng, root, msg = engines.quick_install_any(d)
        except (OSError, ValueError) as e:
            QMessageBox.warning(self, "Быстрая установка", str(e))
            return
        self._log_line(f"$ {eng.title}: {msg}   |   в игре: {engines.HOTKEYS.get(eng.key, 'Shift+T')}")
        if (
            manifest.find_by_root(self.games, root) is None
            and QMessageBox.question(
                self,
                "Готово",
                f"Меню установлено:\n{root}\n\nСтаты найдутся автоматически.\n"
                "Добавить игру и в список студии (чтобы задать свои статы и выдачу)?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            == QMessageBox.StandardButton.Yes
        ):
            if self.cur is not None:
                self._flush_ui_to_model()
            idx = self._add_to_manifest(root, manifest.default_title(root))
            self._reload_list()
            self._select_index(idx)
        else:
            self._reload_list()

    def _remove_game(self):
        if self.cur is None:
            return
        idx = self.cur
        title = self.games.get(idx, {}).get("title", "")
        if (
            QMessageBox.question(
                self,
                "Убрать из списка",
                f"Убрать «{short_title(title)}» из списка?\n\n"
                "Файлы игры не затрагиваются, удаляется только запись в студии.\n"
                "Чтобы снести само меню из игры — используй «Удалить меню».",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        self._flush_ui_to_model()  # правки остальных игр — в памяти, не на диск
        self._commit_structure(lambda gs: gs.pop(idx, None))
        self.cur = None  # правки удаляемой игры отбрасываем
        self._dirty_ids.discard(idx)
        if not self._dirty_ids:
            self._clear_dirty()
        self._log_line(f"$ game_{idx} убрана из списка")
        self._reload_list()
        if self.games:
            self.list.setCurrentRow(0)

    def _reload_from_disk(self):
        if (
            self._dirty
            and QMessageBox.question(
                self,
                "Перечитать",
                "Есть несохранённые правки. Отбросить и перечитать с диска?",
            )
            != QMessageBox.StandardButton.Yes
        ):
            return
        keep = self.cur
        self.games, self.G, self.accent = manifest.load_games()
        self._manifest_mtime = self._manifest_mtime_now()
        self._clear_dirty()
        self.cur = None
        self._reload_list()
        if keep in self.games:
            self._select_index(keep)
        elif self.games:
            self.list.setCurrentRow(0)

    @staticmethod
    def _manifest_mtime_now():
        try:
            return os.path.getmtime(GAMES_DATA_PATH)
        except OSError:
            return None

    def changeEvent(self, e):
        super().changeEvent(e)
        if e.type() == QEvent.Type.ActivationChange and self.isActiveWindow():
            self._manifest_changed_on_disk()

    def _manifest_changed_on_disk(self):
        """Список игр изменили вне студии: без своих правок — перечитать молча, иначе — сказать."""
        m = self._manifest_mtime_now()
        if m is None or m == getattr(self, "_manifest_mtime", m):
            return
        if self._dirty:
            self._manifest_mtime = m  # не напоминать на каждом возврате в окно
            self._log_line("! список игр изменён на диске, а здесь есть несохранённые правки: F5 — перечитать")
            return
        self._reload_from_disk()
        self._log_line("$ список игр изменён на диске — перечитан")

    # ------------------------------------------------------------ QProcess
    def _enqueue(self, script, *args):
        self.queue.append((script, list(args)))
        if self.proc.state() == QProcess.ProcessState.NotRunning:
            self._run_next()

    def _enqueue_current(self, script):
        """Команда над выбранной игрой (без выбора — ничего: «None» в argv ронял скрипт)."""
        if self.cur is not None:
            self._enqueue(script, str(self.cur))

    def _stop_proc(self):
        self.queue.clear()
        if self.proc.state() != QProcess.ProcessState.NotRunning:
            self._log_line("! остановлено пользователем")
            self.proc.kill()

    def _on_proc_error(self, err):
        # FailedToStart не даёт сигнала finished — без этого очередь висела, а кнопки
        # оставались выключенными до перезапуска студии
        if err == QProcess.ProcessError.FailedToStart:
            self._log_line(f"! не удалось запустить процесс: {self.proc.errorString()}")
            self.queue.clear()
            self._set_busy(False)

    def _set_busy(self, busy):
        self.b_stop.setEnabled(busy)
        for b in (self.b_all_dep, self.b_all_ver, self.b_primary):
            b.setEnabled(not busy)
        self.act_check.setEnabled(not busy)
        self.act_uninstall.setEnabled(not busy)
        self.cand_tab.set_busy(busy)

    def _run_next(self):
        if not self.queue:
            return
        script, args = self.queue.pop(0)
        self._set_busy(True)
        self._log_line(f"$ python tm.py {script} {' '.join(args)}")
        self.proc.setWorkingDirectory(ROOT)
        if FROZEN:  # собранная студия: команды tm.py выполняет сам .exe (--tm)
            self.proc.start(sys.executable, ["--tm", script] + args)
        else:
            self.proc.start(sys.executable, [TM_PY, script] + args)

    # ---- лог: цвет по типу строки + «липкий» автоскролл ----
    def _at_bottom(self):
        sb = self.log.verticalScrollBar()
        return sb.value() >= sb.maximum() - 4

    def _append_html(self, html_str):
        sb = self.log.verticalScrollBar()
        stick, prev = self._at_bottom(), sb.value()
        self.log.appendHtml(html_str)
        sb.setValue(sb.maximum() if stick else prev)

    def _on_output(self):
        # stdout приходит кусками — красим только целые строки, «хвост» копим до \n
        self._out_buf += bytes(self.proc.readAllStandardOutput()).decode(
            "utf-8", "replace"
        )
        *lines, self._out_buf = self._out_buf.split("\n")
        for ln in lines:
            self._append_colored(ln)

    def _on_proc_finished(self, code, _status):
        if self._out_buf:  # дописать неполный хвост без \n
            self._append_colored(self._out_buf)
            self._out_buf = ""
        self._log_line(f"  (готово, код {code})")
        if code != 0 and self.queue:  # не раскладывать после провалившегося шага
            self._log_line(
                f"! очередь остановлена: пропущено команд — {len(self.queue)}"
            )
            self.queue.clear()
        self._reload_list()
        if self.cur is not None:
            self.overview.set_installed(self._status_text(self.cur))
            self._set_header(self.cur)
            self._load_cand()
        if self.queue:
            self._run_next()
        else:
            self._set_busy(False)

    def _line_color(self, t):
        """Цвет строки: свои префиксы студии + эвристика по выводу подпроцесса."""
        s = t.lstrip()
        low = t.lower()
        if s.startswith("!"):
            return TOK["err"]
        if s.startswith("$"):
            return ACCENT
        if "готово, код" in t:
            return TOK["ok"] if "код 0" in t else TOK["err"]
        if "traceback" in low or "exception" in low:
            return TOK["err"]
        if re.search(r"\b(errors?|ошибк\w*)\b", low) and not re.search(
            r"\b(0|no|нет)\b[^\n]*error", low
        ):
            return TOK["err"]
        if re.search(r"\b(warnings?|предупрежд\w*)\b", low) and not re.search(
            r"\b0\b[^\n]*warning", low
        ):
            return TOK["warn"]
        return TOK["text_dim"]

    def _append_colored(self, t):
        col = self._line_color(t)
        esc = html.escape(t).replace(" ", "&nbsp;")
        self._append_html(f"<span style='color:{col}'>{esc}</span>")
        self.logp.show_line(t.lstrip("$! "), col)

    def _log_line(self, text):
        self._append_colored(text.rstrip("\n"))

    def closeEvent(self, e):
        if (
            self._dirty
            and QMessageBox.question(
                self, "Выход", "Есть несохранённые правки. Выйти без сохранения?"
            )
            != QMessageBox.StandardButton.Yes
        ):
            e.ignore()
            return
        self.queue.clear()
        if self.proc.state() != QProcess.ProcessState.NotRunning:
            self.proc.kill()
            self.proc.waitForFinished(1500)
        self.settings.setValue("geometry", self.saveGeometry())
        e.accept()


class _LibraryCheck(QThread):
    """Фоновая проверка: устаревшие меню в папке библиотеки и в играх манифеста."""

    done = pyqtSignal(list)

    def __init__(self, folder, games, parent=None):
        super().__init__(parent)
        self.folder, self.games = folder, games

    def run(self):
        from tmkit import library

        stale, seen = [], set()
        try:
            found = library.find_games(self.folder, games=self.games) if self.folder and os.path.isdir(self.folder) else []
            # игры манифеста вне папки библиотеки — тоже
            for i, g in sorted(self.games.items()):
                root = g.get("root", "")
                if root and os.path.exists(root) and not any(
                    os.path.normcase(f.target) == os.path.normcase(os.path.abspath(root)) for f in found
                ):
                    eng = engines.detect_engine(root)
                    if eng is not None:
                        found.append(library.Found(g.get("title") or root, root, root, eng,
                                                   library.status_of(eng, root, generate.render_game(i, g) if eng.key == "renpy" else None), i))
            for f in found:
                key = os.path.normcase(os.path.abspath(f.target))
                if f.status == "stale" and key not in seen:
                    seen.add(key)
                    stale.append(f)
        except Exception:
            stale = []
        self.done.emit(stale)


def main():
    app = QApplication(sys.argv)
    if os.path.exists(ICON_PATH):
        app.setWindowIcon(QIcon(ICON_PATH))  # иконка в таскбаре
    app.setStyleSheet(QSS)
    win = Studio()

    # PyQt6 на необработанном исключении в слоте завершает процесс — вместе с
    # несохранёнными правками. Пишем трейс в лог студии и работаем дальше.
    def _excepthook(tp, val, tb):
        text = "".join(traceback.format_exception(tp, val, tb))
        if sys.__stderr__:
            sys.__stderr__.write(text)
        try:
            for ln in ("необработанная ошибка:\n" + text).splitlines():
                win._log_line("! " + ln)
        except Exception:
            pass

    sys.excepthook = _excepthook

    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
