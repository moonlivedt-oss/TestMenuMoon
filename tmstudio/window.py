"""Главное окно студии: список игр, вкладки карточки, лог и очередь команд tm.py.

Команды пайплайна (collect / curate / gen / deploy / verify / uninstall) идут отдельным
процессом `python tm.py <команда> N` через QProcess — окно не замирает, вывод — в логе.
"""

import os, sys, re, html, traceback

from PyQt6.QtCore import Qt, QProcess, QProcessEnvironment, QSettings, QSize, QThread, QTimer, pyqtSignal
from PyQt6.QtGui import QColor, QIcon, QPixmap, QKeySequence, QShortcut
from PyQt6.QtWidgets import (
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
    QPlainTextEdit,
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
from tmkit.paths import CAND_DIR, ana_dir
from tmkit import naming  # понятные имена переменных (словарь — из движка)

from tmstudio import ROOT, tour
from tmstudio.theme import (
    ACCENT, DIRTY_MARK, ENGINE_BADGE, ICON_DIR, ICON_PATH, QSS,
    add_shadow, faded_icon, ibtn, icon, mascot_box,
)
from tmstudio.tabs import OverviewTab, TableTab, CandidatesTab

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
        self._reload_list()
        if self.games:
            self.list.setCurrentRow(0)
        if self.settings.value("tour_done", False, type=bool) is not True:
            QTimer.singleShot(500, self.start_tour)
        QTimer.singleShot(1500, self._check_library)

    def start_tour(self):
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
    def _build_ui(self):
        root = QSplitter(Qt.Orientation.Vertical)

        top = QSplitter(Qt.Orientation.Horizontal)

        # ---- левая колонка: игры + глобальные действия ----
        left = QWidget()
        lv = QVBoxLayout(left)
        lv.setContentsMargins(0, 0, 0, 0)
        lv.setSpacing(8)
        head = QHBoxLayout()
        head.setSpacing(11)
        if os.path.exists(ICON_PATH):
            ic = QLabel()
            ic.setPixmap(
                QPixmap(ICON_PATH).scaled(
                    44,
                    44,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            add_shadow(ic, blur=18, dy=4, alpha=170)
            head.addWidget(ic)
        tv = QVBoxLayout()
        tv.setSpacing(0)
        title = QLabel("Test Menu Studio")
        title.setObjectName("h1")
        sub = QLabel("тулкит тест-меню | мульти-движок")
        sub.setObjectName("sub")
        tv.addWidget(title)
        tv.addWidget(sub)
        head.addLayout(tv)
        head.addStretch(1)
        self.b_tour = ibtn("Обучение", "question", "Пошаговый тур по студии")
        self.b_tour.clicked.connect(self.start_tour)
        head.addWidget(self.b_tour, 0, Qt.AlignmentFlag.AlignTop)
        lv.addLayout(head)
        # плашка «меню устарело в N играх» — проверка библиотеки при запуске (_check_library)
        self.update_bar = QWidget(objectName="updatebar")
        self.update_bar.setStyleSheet(
            "#updatebar { background: rgba(240,180,41,0.12); border: 1px solid rgba(240,180,41,0.55);"
            " border-radius: 12px; }"
        )
        ub = QHBoxLayout(self.update_bar)
        ub.setContentsMargins(10, 6, 6, 6)
        self.update_lbl = QLabel("")
        self.update_lbl.setWordWrap(True)
        ub.addWidget(self.update_lbl, 1)
        self.b_update = QPushButton("Обновить")
        self.b_update.setObjectName("primary")
        self.b_update.clicked.connect(self._update_stale)
        b_hide = ibtn("", "close", "Скрыть до следующего запуска")
        b_hide.clicked.connect(self.update_bar.hide)
        ub.addWidget(self.b_update)
        ub.addWidget(b_hide)
        self.update_bar.hide()
        lv.addWidget(self.update_bar)
        lv.addWidget(QLabel("ИГРЫ ИЗ МАНИФЕСТА", objectName="section"))
        self.list_filter = QLineEdit()
        self.list_filter.setPlaceholderText("фильтр игр…")
        self.list_filter.setClearButtonEnabled(True)
        self.list_filter.textChanged.connect(self._filter_list)
        lv.addWidget(self.list_filter)
        self.list = QListWidget()
        self.list.currentRowChanged.connect(self._on_select)
        lv.addWidget(self.list, 1)
        self.list_empty = mascot_box(
            "m_wave", "Игр пока нет. «Добавить» — игра в манифест, или быстрая установка ниже."
        )
        self.list_empty.hide()
        lv.addWidget(self.list_empty)

        mb = QHBoxLayout()
        b_add = ibtn("Добавить", "plus", "Добавить игру в манифест (выбрать папку game/)")
        self.b_add_game = b_add
        b_add.clicked.connect(self._add_game)
        b_rem = ibtn("Убрать", "trash", "Убрать выбранную игру из манифеста (файлы игры не трогаются)")
        b_rem.setObjectName("danger")
        b_rem.clicked.connect(self._remove_game)
        mb.addWidget(b_add)
        mb.addWidget(b_rem)
        mb.addStretch(1)
        lv.addLayout(mb)

        b_quick = ibtn("Быстрая установка в любую игру…", "download")
        self.b_quick = b_quick
        b_quick.setToolTip(
            "Поставить меню в игру Ren'Py без манифеста и пайплайна: только движок.\n"
            "Статы меню найдёт само (режим «авто»), подсказки к выборам и сканер тоже работают."
        )
        b_quick.clicked.connect(self._quick_install)
        lv.addWidget(b_quick)
        b_lib = ibtn(
            "Библиотека игр…",
            "house",
            "Указать папку с играми: студия найдёт все игры, покажет движок и состояние меню, "
            "поставит или обновит меню пачкой",
        )
        b_lib.clicked.connect(self._open_library)
        lv.addWidget(b_lib)
        b_saves = ibtn("Сохранения…", "save", "Редактор сохранений выбранной игры: Ren'Py, RPG Maker, Unity (PlayerPrefs, JSON), Godot")
        b_saves.clicked.connect(self._open_saves)
        lv.addWidget(b_saves)

        gb = QHBoxLayout()
        self.b_all_dep = ibtn("Разложить всё", "upload")
        self.b_all_dep.setObjectName("primary")
        self.b_all_dep.clicked.connect(self._deploy_all)
        self.b_all_ver = ibtn("Проверить всё", "checklist", "Lint всех игр Ren'Py из манифеста")
        self.b_all_ver.clicked.connect(lambda: self._enqueue("verify"))
        b_reload = ibtn("", "back", "Перечитать манифест с диска")
        b_reload.clicked.connect(self._reload_from_disk)
        gb.addWidget(self.b_all_dep)
        gb.addWidget(self.b_all_ver)
        gb.addWidget(b_reload)
        lv.addLayout(gb)
        top.addWidget(left)

        # ---- правая колонка: вкладки ----
        self.overview = OverviewTab(
            on_dirty=self._mark_dirty,
            on_save=self._save_manifest,
            on_save_deploy=self._save_and_deploy,
            on_validate=self._validate_current,
            on_verify=lambda: self._enqueue_current("verify"),
            on_open=self._open_folder,
            on_uninstall=self._uninstall,
            on_launch=self._launch_current,
            default_accent=self.accent,
        )
        self.stats_tab = TableTab(
            ["Метка", "Путь (пусто = заголовок секции)", "min", "max"],
            "путь резолвится на store игры",
            self._mark_dirty,
        )
        self.actions_tab = TableTab(
            ["Метка", "Код (пусто = заголовок секции)"],
            "код исполняется в пространстве игры",
            self._mark_dirty,
        )
        self.cand_tab = CandidatesTab(
            f"{CAND_DIR}/game_N.txt — подсказки: пути статов, инвентарь. "
            "После «//» — понятное имя (с пометкой «догадка», если только по названию)",
            on_collect=lambda: self._enqueue_current("collect"),
            on_curate=self._run_curate,
            on_refresh=self._load_cand,
            on_full=self._full_pipeline,
            on_add_stats=self._add_stats_from_candidates,
        )

        self.tabs = QTabWidget()
        self.tabs.setIconSize(QSize(20, 20))
        self.tabs.addTab(self.overview, icon("house"), "Обзор")
        self.tabs.addTab(self.stats_tab, icon("stats"), "Характеристики")
        self.tabs.addTab(self.actions_tab, icon("actions"), "Действия")
        self.tabs.addTab(self.cand_tab, icon("scanner"), "Кандидаты")
        top.addWidget(self.tabs)
        top.setStretchFactor(0, 0)
        top.setStretchFactor(1, 1)
        top.setSizes([330, 850])
        root.addWidget(top)

        # ---- лог ----
        logw = QWidget()
        lgl = QVBoxLayout(logw)
        lgl.setContentsMargins(0, 6, 0, 0)
        lh = QHBoxLayout()
        lh.addWidget(QLabel("ЛОГ", objectName="section"))
        lh.addStretch(1)
        self.b_stop = ibtn("Стоп", "close", px=16)
        self.b_stop.setObjectName("danger")
        self.b_stop.setToolTip("Прервать текущую команду и очистить очередь")
        self.b_stop.setEnabled(False)
        self.b_stop.clicked.connect(self._stop_proc)
        b_clr = ibtn("Очистить", "brush", px=16)
        b_clr.clicked.connect(lambda: self.log.clear())
        lh.addWidget(self.b_stop)
        lh.addWidget(b_clr)
        lgl.addLayout(lh)
        self.log = QPlainTextEdit()
        self.log.setObjectName("log")
        self.log.setReadOnly(True)
        lgl.addWidget(self.log)
        root.addWidget(logw)
        root.setStretchFactor(0, 3)
        root.setStretchFactor(1, 1)
        root.setSizes([560, 200])

        wrap = QWidget()
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(12, 12, 12, 12)
        wl.addWidget(root)
        self.setCentralWidget(wrap)

    # ------------------------------------------------------------ модель/список
    def _reload_list(self):
        self.list.blockSignals(True)
        self.list.clear()
        for i in sorted(self.games):
            g = self.games[i]
            root = g.get("root", "")
            eng = engines.detect_engine(root)
            st = self._status(i, eng)
            installed = st != "none"
            n_stat = len([s for s in g.get("stats", []) if s[1]])
            n_act = len([a for a in g.get("actions", []) if a[1]])
            bits = [ENGINE_BADGE.get(eng.key, eng.key) if eng else "?"]
            if n_stat:
                bits.append(f"статы:{n_stat}")
            if n_act:
                bits.append(f"выдача:{n_act}")
            extra = "  | " + " | ".join(bits)
            mark = DIRTY_MARK if i in self._dirty_ids else ""
            it = QListWidgetItem(f"game_{i} — {g.get('title', '')}{extra}{mark}")
            it.setIcon(
                icon("ok") if st == "ok" else icon("warn") if st == "stale" else faded_icon("ok")
            )
            it.setToolTip(
                {"ok": "Меню установлено, версия актуальная",
                 "stale": "Меню устарело — «Сохранить и разложить»",
                 "none": "Меню не установлено"}[st]
            )
            it.setData(Qt.ItemDataRole.UserRole, i)
            it.setForeground(QColor("#e8eaee" if installed else "#8b919d"))
            self.list.addItem(it)
            if i == self.cur:  # clear() сбрасывает выделение — вернуть
                self.list.setCurrentItem(
                    it
                )  # (сигналы заглушены: UI игры уже загружен)
        self.list.blockSignals(False)
        self.list_empty.setVisible(not self.games)
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
        self.overview.set_renpy(renpy_mode)
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
        """Включить только вкладки, релевантные движку (None -> Ren'Py-манифест, всё вкл).
        Индексы вкладок: 0 Обзор, 1 Характеристики, 2 Действия, 3 Кандидаты."""
        gen = eng.supports("generate") if eng else True  # статы/действия из манифеста
        scan = eng.supports("scan") if eng else True  # поиск кандидатов
        self.tabs.setTabEnabled(1, gen)
        self.tabs.setTabEnabled(2, gen)
        self.tabs.setTabEnabled(3, scan)
        if not self.tabs.isTabEnabled(self.tabs.currentIndex()):
            self.tabs.setCurrentIndex(0)

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
            "ok": "да, актуальная версия",
            "stale": "устарело — нажми «Сохранить и разложить»",
            "none": "нет — нажми «Сохранить и разложить»",
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
                if not it.text().endswith(DIRTY_MARK):
                    it.setText(it.text() + DIRTY_MARK)
                break

    def _save_manifest(self):
        self._flush_ui_to_model()
        manifest.save_games(self.games, self.G, self.accent)
        self._clear_dirty()
        self._log_line("$ манифест сохранён -> tmkit/games_data.py")
        self._reload_list()
        if self.cur is not None:
            self.overview.set_installed(self._status_text(self.cur))

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
                self, "Удалить меню", f"Удалить тест-меню из game_{self.cur}?"
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
            QMessageBox.information(self, "Проверка данных", "Проблем не найдено ✓")
        else:
            QMessageBox.warning(
                self,
                "Проверка данных",
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
            f"$ в Характеристики game_{self.cur}: добавлено {n}, уже было {len(pairs) - n}"
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
                "Пайплайн отменён",
                "Синтаксические ошибки в действиях:\n\n" + "\n".join(syntax),
            )
            self._log_line(
                "$ пайплайн отменён: синтаксис в действиях (%d)" % len(syntax)
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
                    "Нажми «1. Распаковать исходники», затем «2. Найти кандидатов»."
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
        names = ", ".join(g.name for g in stale[:3]) + (" …" if len(stale) > 3 else "")
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

    def _open_library(self):
        from tmstudio.library import LibraryDialog

        LibraryDialog(self, self.games, self._add_to_manifest, self._library_changed).exec()

    def _library_changed(self):
        self._reload_list()
        if self.cur is not None:
            self.overview.set_installed(self._status_text(self.cur))

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
                    "Игра уже в манифесте",
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
        from tmstudio import save_editor

        root = self.games[self.cur].get("root", "") if self.cur is not None else ""
        eng = engines.detect_engine(root) if root else None
        save_editor.SaveEditor(self, game_root=root or None, engine_key=eng.key if eng else None).exec()

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
                "Добавить игру и в манифест (чтобы задать свои статы/действия)?",
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
                "Убрать из манифеста",
                f"Убрать game_{idx} — «{title}» — из манифеста?\n\n"
                "Файлы игры и build/ не затрагиваются; удаляется только запись.\n"
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
        self._log_line(f"$ game_{idx} убрана из манифеста")
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
        self.games, self.G, self.accent = manifest.load_games()
        self._clear_dirty()
        self.cur = None
        self._reload_list()
        if self.games:
            self.list.setCurrentRow(0)

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
        for b in (self.b_all_dep, self.b_all_ver):
            b.setEnabled(not busy)
        self.overview.set_busy(busy)
        self.cand_tab.set_busy(busy)

    def _run_next(self):
        if not self.queue:
            return
        script, args = self.queue.pop(0)
        self._set_busy(True)
        self._log_line(f"$ python tm.py {script} {' '.join(args)}")
        self.proc.setWorkingDirectory(ROOT)
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
            return "#ff6b6b"
        if s.startswith("$"):
            return ACCENT
        if "готово, код" in t:
            return "#5ad469" if "код 0" in t else "#ff6b6b"
        if "traceback" in low or "exception" in low:
            return "#ff6b6b"
        if re.search(r"\b(errors?|ошибк\w*)\b", low) and not re.search(
            r"\b(0|no|нет)\b[^\n]*error", low
        ):
            return "#ff6b6b"
        if re.search(r"\b(warnings?|предупрежд\w*)\b", low) and not re.search(
            r"\b0\b[^\n]*warning", low
        ):
            return "#f0b429"
        return "#cdd3dc"

    def _append_colored(self, t):
        esc = html.escape(t).replace(" ", "&nbsp;")
        self._append_html(f"<span style='color:{self._line_color(t)}'>{esc}</span>")

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
