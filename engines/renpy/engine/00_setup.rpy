# =====================================================================
#  UNIVERSAL TEST MENU  —  shared engine  (drop-in, идентичен для всех игр)
#  Открыть/закрыть:  Shift+T   (запасная клавиша: F9)
#  Подсказки к выборам: Shift+H
#  Вкладки: Перемотка | Переменные | Выдать | Поиск | Сюжет | Настройки
#  (значки — game/tm_ui/ic/*.png; нет папки — вкладки просто без значков)
#  Окно можно перетаскивать за шапку. Клики/клавиши в игру не проходят.
#  data-файл (zzz_testmenu_data.rpy: заголовок / акцент / статы / действия)
#  НЕ обязателен: без него статы находятся автоматически (режим «авто»).
# =====================================================================

# ---- щедрый rollback + разрешённый скип ----
# Настройки игрока (_preferences) здесь НЕ трогаем: они живут в persistent и остались бы
# изменёнными после удаления меню. Скип непрочитанного включается только на время скипа
# из меню (tm_start_skip) или явно переключателем на вкладке «Перемотка».
init 999 python:
    try:
        # Откат включён, но глубина — разумная: НЕ больше, чем нужно для «Назад ×10».
        # Раньше тут стояло 100000: журнал отката рос бесконечно и целиком писался в
        # каждый сейв (в большой игре — 300 МБ несжатого журнала, 31 МБ файл),
        # автосейв замирал на секунды, игра лагала. Значения игры, если они больше, не трогаем.
        config.rollback_enabled = True
        config.hard_rollback_limit = max(int(config.hard_rollback_limit or 0), 128)
        config.rollback_length = max(int(config.rollback_length or 0), 128)
    except Exception:
        pass
    try:
        # Скип разрешён всегда (Ctrl / Tab), даже если игра его отключила.
        # Alt клавишей скипа больше не назначаем: Alt+Tab и Alt+Enter запускали пропуск.
        config.allow_skipping = True
        config.fast_skipping = True
        if (not getattr(config, "skip_delay", 0)) or config.skip_delay > 40:
            config.skip_delay = 20
    except Exception:
        pass

# ---- дефолты заголовка/акцента (data-файл переопределит) ----
init -10 python:
    if not hasattr(store, "tm_title"):
        store.tm_title = "TEST MENU"
    if not hasattr(store, "tm_accent"):
        store.tm_accent = "#38e0c8"
    if not hasattr(store, "tm_stats"):
        store.tm_stats = []
    if not hasattr(store, "tm_actions"):
        store.tm_actions = []

    class _TmUI(NoRollback):
        # NoRollback: поля не откатываются. Объект создаётся на init и его привязка
        # не меняется, поэтому в сохранения он тоже не попадает.
        def __init__(self):
            self.open = False
            self.tab = "rewind"
            self.stat_step = 1
            self.win_pos = None       # (x, y) окна после перетаскивания; None = по центру
            self.diag_open = False
            self.diag = []
            self.stat_filter = ""
            self.act_filter = ""
            self.give_qty = 1
            self.scan_val = ""        # сканер: поле поиска по значению
            self.jump_label = ""      # настройки: поле «перейти к метке»
            self.extra = []           # статы, добавленные из сканера: [(метка, путь)]
            self.frozen = {}          # заморозка: путь -> удерживаемое значение
            self.profile = {}         # профиль игры: {"frozen": {путь: значение}, "modes": {путь: вид}}
            self.stats_mode = None    # "data" | "auto"; None = data, если он задан, иначе авто
            self.stat_page = 0
            self.watch = []           # HUD наблюдения: [(метка, путь)]
            self.hud_on = True
            self.find_text = ""       # сюжет: поиск реплики по тексту
            self.flag_filter = ""     # сюжет: фильтр persistent-флагов
            self.confirm = ""         # ключ действия, ждущего подтверждения вторым кликом
            self.accent = None        # текущий акцент (не в store: иначе он писался в каждый сейв)
            self.slots = None         # кэш «пусто / время» быстрых слотов (диск не на каждый кадр)
            self.skip_restore = None  # настройки скипа игрока до скипа из меню — вернуть после
            self.help_open = False    # окно «Как пользоваться» (само открывается в первый раз)
            self.show_service = False # авто-список: показать группу «Служебное»
            self.journal = []         # правки из меню: [(путь, было, стало)] — для отмены
            self.changelog = []       # журнал изменений: [(время, где, путь, было, стало, кто)]
            self.log_prev = {}        # журнал: прошлое значение пути
            self.log_src = {}         # журнал: путь -> кто изменил («меню» / «заморозка»), иначе «игра»
            self.log_open = False     # окно журнала изменений
            self.bridge = False       # пульт в студии включён (12_bridge.rpy)
            self.favs = []            # избранное: пути, закреплённые наверху «Переменных»
            self.seen = None          # значения при прошлом открытии меню: {путь: значение}
            self.deltas = {}          # что изменилось с прошлого открытия: {путь: (было, стало)}
            self.only_changed = False # «Переменные»: показать только изменённые
            self.freeze_mode = {}     # заморозка: путь -> "eq" (ровно) | "ge" (не меньше) | "le" (не больше)
            self.mini = False         # мини-режим: плашка с кнопками поверх игры
            self.toasts = []          # свои уведомления: [(время, текст, вид)]
            self.tick = 0             # номер взаимодействия (для вспышек HUD)
            self.hud_last = {}        # HUD: прошлое значение пути
            self.hud_flash = {}       # HUD: путь -> (изменение, время)
            self.history = []         # история выборов: [{"text", "where", "eff"}]
            self.hist_pending = None  # выбор сделан, эффект ещё не посчитан: (текст, где, снимок)
            self.edit = None          # окно ввода: ("value" | "name", путь) или None
            self.edit_text = ""
            self.edit_err = ""
            self.where_open = False   # окно «Где я»
            self.jump_mode = "jump"   # «Сюжет»: метка — прыжок или повтор сцены (Replay)
            self.peek = set()         # подсказки «по щелчку»: открытые варианты (узел, индекс)
            self.state_sig = None     # последний записанный tm_state.json (пишем только изменения)
            # --- вкладка «Тест» (2026-10-06) ---
            self.auto = None          # авто-прохождение: dict (режим, лимит, стоп-условия, маршрут) или None
            self.auto_mode = "new"    # стратегия выбора: new | random | first
            self.auto_limit = 30      # сколько выборов сделать (0 — без ограничения)
            self.auto_stop_label = "" # остановиться на этой метке
            self.auto_stop_unseen = False  # остановиться на первой непрочитанной реплике
            self.auto_log = []        # что сделало последнее авто-прохождение: [текст]
            self.route_rec = []       # выборы текущей партии: [(текст варианта, точка отката)]
            self.route_start = ""     # откуда записан: "start" — с начала игры, "save" — с загрузки
            self.routes = []          # сохранённые маршруты: [{"name", "choices"}]
            self.scene_filter = ""    # «Тест»: фильтр сцен
            self.scene_open = ""      # «Тест»: сцена, у которой раскрыто «откуда сюда»
            self.scene_all = False    # «Тест»: показывать и просмотренные сцены
            self.code_peek = set()    # подсказки: варианты с раскрытым кодом (узел, индекс)
            self.code_text = ""       # «Код»: строка Python
            self.code_hist = []       # «Код»: [(код, результат, ошибка?)]
            self.hud_expr = ""        # «Настройки»: выражение для HUD
            self.char_names = {}      # свои имена персонажей: {переменная: имя}
            self.char_orig = {}       # исходные имена переименованных: {переменная: имя}
            self.bug_shot = None      # скриншот к заметке о баге (снят до открытия окна)
            self.bug_pending = False  # меню спрятано, через кадр снимаем экран для заметки
            self.label_prev = None    # чужой config.label_callback (цепочка)

    tm_ui = _TmUI()

    def tm_acc():
        # акцент для экранов: тема (tm_ui.accent) -> data-файл -> по умолчанию
        return tm_ui.accent or getattr(store, "tm_accent", None) or "#38e0c8"

# Встроенный в Ren'Py шрифт с кириллицей — не зависим от шрифта игры.
define tm_font = "DejaVuSans.ttf"

# Состояние самого меню (открыто/вкладка/шаг/фильтры/заморозка) — в объекте tm_ui
# (см. _TmUI ниже), состояние сканера — в renpy.session. Ни то ни другое НЕ пишется
# в сейвы и НЕ откатывается: раньше «Назад» откатывал и флаг «меню открыто», и меню
# закрывалось после каждого шага перемотки.

