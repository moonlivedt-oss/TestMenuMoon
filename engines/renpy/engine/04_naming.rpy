# ============================ hotkey (глобально) ============================
# ==================== смысл переменных: имена, «что делает», пороги ====================
# Понятное имя (персонаж + перевод слов имени + подпись из реплик), где переменная меняется
# и где проверяется (по AST сценария, работает и с .rpyc), пороги условий, группы по смыслу.
# Словарь TM_WORDS — единственный: студия (tmkit/naming.py) читает его из этого файла,
# поэтому он должен оставаться литералом { u"слово": u"перевод", ... } с «}» на своей строке.
init -4 python:
    TM_WORDS = {
        u"love": u"симпатия", u"affection": u"привязанность", u"affect": u"привязанность",
        u"lust": u"страсть", u"corruption": u"развращённость", u"corrupt": u"развращённость",
        u"trust": u"доверие", u"money": u"деньги", u"cash": u"деньги", u"gold": u"золото",
        u"coin": u"монеты", u"coins": u"монеты", u"dollar": u"доллары", u"credit": u"кредиты",
        u"point": u"очки", u"points": u"очки", u"strength": u"сила", u"str": u"сила",
        u"charm": u"обаяние", u"charisma": u"обаяние", u"cha": u"обаяние",
        u"intelligence": u"интеллект", u"intel": u"интеллект", u"int": u"интеллект",
        u"smart": u"ум", u"dex": u"ловкость", u"agility": u"ловкость", u"wis": u"мудрость",
        u"wisdom": u"мудрость", u"luck": u"удача", u"relationship": u"отношения",
        u"relation": u"отношения", u"relat": u"отношения", u"rel": u"отношения",
        u"xp": u"опыт", u"exp": u"опыт", u"experience": u"опыт", u"level": u"уровень",
        u"lvl": u"уровень", u"energy": u"энергия", u"health": u"здоровье", u"hp": u"здоровье",
        u"mana": u"мана", u"mp": u"мана", u"karma": u"карма", u"arousal": u"возбуждение",
        u"arous": u"возбуждение", u"horny": u"возбуждение", u"submission": u"покорность",
        u"submissive": u"покорность", u"submi": u"покорность", u"dominance": u"доминирование",
        u"domin": u"доминирование", u"respect": u"уважение", u"friendship": u"дружба",
        u"friend": u"дружба", u"mood": u"настроение", u"happiness": u"счастье",
        u"happy": u"счастье", u"sanity": u"рассудок", u"fame": u"слава",
        u"reputation": u"репутация", u"reput": u"репутация", u"rep": u"репутация",
        u"skill": u"навык", u"stamina": u"выносливость", u"obedience": u"послушание",
        u"obed": u"послушание", u"lewd": u"пошлость", u"intimacy": u"близость",
        u"intim": u"близость", u"desire": u"желание", u"slut": u"распущенность",
        u"confidence": u"уверенность", u"confid": u"уверенность", u"courage": u"смелость",
        u"stress": u"стресс", u"fatigue": u"усталость", u"tired": u"усталость",
        u"hunger": u"голод", u"thirst": u"жажда", u"score": u"счёт",
        u"influence": u"влияние", u"influen": u"влияние", u"loyalty": u"верность",
        u"loyal": u"верность", u"jealousy": u"ревность", u"jealous": u"ревность",
        u"suspicion": u"подозрение", u"suspic": u"подозрение", u"attraction": u"влечение",
        u"attract": u"влечение", u"passion": u"страсть", u"romance": u"романтика",
        u"fitness": u"форма", u"power": u"сила", u"willpower": u"сила воли",
        u"day": u"день", u"days": u"дни", u"week": u"неделя", u"weekday": u"день недели",
        u"month": u"месяц", u"year": u"год", u"time": u"время", u"hour": u"час",
        u"hours": u"часы", u"minute": u"минуты", u"daytime": u"время суток",
        u"chapter": u"глава", u"episode": u"эпизод", u"count": u"счётчик",
        u"counter": u"счётчик", u"total": u"всего", u"max": u"максимум", u"min": u"минимум",
        u"inventory": u"инвентарь", u"inv": u"инвентарь", u"item": u"предмет",
        u"items": u"предметы", u"key": u"ключ", u"keys": u"ключи", u"met": u"встреча",
        u"meet": u"встреча", u"seen": u"видел", u"saw": u"видел", u"visited": u"был",
        u"visit": u"посещение", u"done": u"сделано", u"finished": u"завершено",
        u"unlocked": u"открыто", u"unlock": u"открыто", u"quest": u"задание",
        u"task": u"задание", u"mission": u"задание", u"progress": u"прогресс",
        u"stage": u"этап", u"step": u"шаг", u"route": u"ветка", u"path": u"путь",
        u"ending": u"концовка", u"end": u"концовка", u"kiss": u"поцелуй",
        u"kissed": u"поцелуй", u"date": u"свидание", u"dated": u"свидание",
        u"sex": u"секс", u"gift": u"подарок", u"gifts": u"подарки", u"talk": u"разговор",
        u"talked": u"разговор", u"work": u"работа", u"job": u"работа", u"salary": u"зарплата",
        u"debt": u"долг", u"bank": u"банк", u"rent": u"аренда", u"food": u"еда",
        u"bonus": u"бонус", u"name": u"имя", u"mom": u"мама", u"mother": u"мама",
        u"dad": u"папа", u"father": u"папа", u"sister": u"сестра", u"sis": u"сестра",
        u"brother": u"брат", u"aunt": u"тётя", u"girlfriend": u"девушка", u"gf": u"девушка",
        u"wife": u"жена", u"teacher": u"учитель", u"boss": u"босс",
        u"location": u"место", u"place": u"место", u"room": u"комната", u"outfit": u"одежда",
        u"clothes": u"одежда", u"photo": u"фото", u"photos": u"фото", u"secret": u"секрет",
        u"choice": u"выбор", u"choices": u"выборы", u"cheat": u"чит", u"bad": u"плохое",
        u"good": u"хорошее", u"angry": u"злость", u"anger": u"злость", u"fear": u"страх",
        u"pain": u"боль", u"pleasure": u"удовольствие", u"naughty": u"шалость",
        u"pervert": u"извращённость", u"perv": u"извращённость", u"shame": u"стыд",
        u"cum": u"оргазм", u"orgasm": u"оргазм", u"virgin": u"девственность",
        u"pregnant": u"беременность", u"preg": u"беременность", u"drunk": u"опьянение",
        u"alcohol": u"алкоголь", u"beer": u"пиво", u"wine": u"вино", u"phone": u"телефон",
        u"car": u"машина", u"house": u"дом", u"home": u"дом", u"school": u"школа",
        u"class": u"урок", u"exam": u"экзамен", u"grade": u"оценка", u"study": u"учёба",
        u"gym": u"спортзал", u"train": u"тренировка", u"training": u"тренировка",
        u"next": u"следующий", u"son": u"сын", u"daughter": u"дочь", u"husband": u"муж",
        u"decency": u"приличие", u"hygiene": u"гигиена", u"buddy": u"приятель",
        u"nerd": u"ботаник", u"student": u"студент", u"college": u"колледж", u"beach": u"пляж",
        u"city": u"город", u"shop": u"магазин", u"chastity": u"пояс верности",
        u"caged": u"в клетке", u"tattoo": u"татуировка", u"piercing": u"пирсинг",
        u"diary": u"дневник", u"storyline": u"сюжетная линия", u"storylines": u"сюжетные линии",
        u"bully": u"хулиган", u"librarian": u"библиотекарь", u"customer": u"клиент",
        u"morning": u"утро", u"cost": u"расход", u"due": u"срок", u"facial": u"на лице",
        u"neighbor": u"сосед", u"neighbors": u"соседи", u"introduced": u"знакомство",
        u"daily": u"за день", u"body": u"тело", u"empathy": u"эмпатия", u"efficient": u"эффективная",
        u"sp": u"очки навыков", u"knows": u"знает", u"happened": u"было",
        # экшен, RPG, выживание: те же правила, что и для статов новелл
        u"ammo": u"патроны", u"bullet": u"патроны", u"bullets": u"патроны", u"clip": u"обойма",
        u"magazine": u"магазин", u"grenade": u"гранаты", u"grenades": u"гранаты",
        u"weapon": u"оружие", u"weapons": u"оружие", u"armor": u"броня", u"armour": u"броня",
        u"shield": u"щит", u"defense": u"защита", u"defence": u"защита", u"def": u"защита",
        u"attack": u"атака", u"atk": u"атака", u"damage": u"урон", u"dmg": u"урон",
        u"crit": u"крит", u"critical": u"крит", u"speed": u"скорость", u"spd": u"скорость",
        u"jump": u"прыжок", u"lives": u"жизни", u"life": u"жизнь", u"kill": u"убийства",
        u"kills": u"убийства", u"death": u"смерти", u"deaths": u"смерти", u"wave": u"волна",
        u"enemy": u"враги", u"enemies": u"враги", u"combo": u"комбо", u"gem": u"кристаллы",
        u"gems": u"кристаллы", u"diamond": u"алмазы", u"diamonds": u"алмазы",
        u"crystal": u"кристаллы", u"crystals": u"кристаллы", u"ore": u"руда", u"wood": u"дерево",
        u"stone": u"камень", u"iron": u"железо", u"potion": u"зелья", u"potions": u"зелья",
        u"fuel": u"топливо", u"oxygen": u"кислород", u"water": u"вода", u"medkit": u"аптечки",
        u"bandage": u"бинты", u"battery": u"батарея", u"lockpick": u"отмычки", u"magic": u"магия",
        u"spell": u"заклинание", u"cooldown": u"перезарядка", u"timer": u"таймер",
        u"distance": u"расстояние", u"vitality": u"живучесть", u"vit": u"живучесть",
        u"endurance": u"стойкость", u"perception": u"восприятие",
        u"accuracy": u"точность", u"resist": u"сопротивление",
        u"upgrade": u"улучшение", u"upgrades": u"улучшения", u"tier": u"уровень", u"rank": u"ранг",
        u"prestige": u"престиж", u"souls": u"души", u"essence": u"эссенция", u"scrap": u"лом",
        u"parts": u"детали", u"material": u"материалы", u"materials": u"материалы",
        u"resource": u"ресурсы", u"resources": u"ресурсы", u"highscore": u"рекорд",
        u"best": u"лучший", u"multiplier": u"множитель", u"mult": u"множитель",
        u"boost": u"усиление", u"regen": u"регенерация", u"chance": u"шанс", u"drop": u"добыча",
        u"loot": u"добыча", u"temperature": u"температура", u"heat": u"жар",
        u"radiation": u"радиация", u"ammunition": u"патроны", u"arrow": u"стрелы",
        u"arrows": u"стрелы", u"bomb": u"бомбы", u"bombs": u"бомбы", u"star": u"звёзды",
        u"stars": u"звёзды",
    }
    # по префиксу слово совпадает, только если остаток — окончание (love-s, kiss-ed, train-ing);
    # у основ (не самостоятельных слов) остаток любой: arous-al, domin-ance, reput-ation
    TM_INFLECT = (u"s", u"es", u"d", u"ed", u"ing", u"ion", u"ions", u"ness", u"ity", u"ment",
                  u"y", u"ies", u"ful", u"al", u"ly", u"ship", u"ance", u"ence", u"ive", u"ant", u"ent")
    TM_STEMS = frozenset((u"arous", u"submi", u"domin", u"reput", u"influen", u"intim", u"confid",
                          u"suspic", u"relat", u"corrupt", u"attract", u"obed", u"intel", u"affect"))
    # служебные слова имён: не переводятся и не попадают в подпись
    TM_GENERIC = frozenset((u"stat", u"stats", u"data", u"var", u"vars", u"game", u"player",
                            u"pc", u"mc", u"store", u"value", u"val", u"info", u"the", u"is",
                            u"has", u"my", u"current", u"cur", u"num", u"lvl", u"character",
                            u"char", u"state", u"flags", u"flag", u"temp"))
    TM_MONEY = frozenset((u"money", u"cash", u"gold", u"coin", u"coins", u"dollar", u"credit",
                          u"gem", u"gems", u"diamond", u"diamonds"))
    TM_INV = frozenset((u"inv", u"inventory", u"item", u"items", u"bag", u"backpack", u"ammo",
                        u"potion", u"potions", u"medkit", u"weapon", u"weapons", u"loot"))
    TM_TIME = frozenset((u"day", u"days", u"week", u"weekday", u"month", u"year", u"time",
                         u"hour", u"hours", u"minute", u"daytime", u"chapter", u"episode"))

    _TM_COND_NUM = _tm_re.compile(
        r'([A-Za-z_][\w\.]*(?:\[[^\]]+\])*(?:\.\w+)*)\s*(>=|<=|==|!=|>|<)\s*(-?\d+(?:\.\d+)?)')
    _TM_COND_NUM_R = _tm_re.compile(
        r'(-?\d+(?:\.\d+)?)\s*(>=|<=|==|!=|>|<)\s*([A-Za-z_][\w\.]*(?:\[[^\]]+\])*(?:\.\w+)*)')
    _TM_COND_NAME = _tm_re.compile(r'(?<![\w\.\]"\'])([A-Za-z_][\w\.]*(?:\[[^\]]+\])*)')
    _TM_SAY_AFTER = _tm_re.compile(r'\[([A-Za-z_][\w\.]*(?:\[[^\]]+\])*)(?:![a-z]+)?\]\s*([^\W\d_]{3,})', _tm_re.U)
    _TM_SAY_BEFORE = _tm_re.compile(r'([^\W\d_]{3,})\s*:\s*\[([A-Za-z_][\w\.]*(?:\[[^\]]+\])*)(?:![a-z]+)?\]', _tm_re.U)
    _TM_FLIP = {">=": "<=", "<=": ">=", ">": "<", "<": ">", "==": "==", "!=": "!="}
    _TM_KEYWORDS = frozenset(("and", "or", "not", "in", "is", "True", "False", "None", "if",
                              "else", "lambda", "renpy", "store", "persistent", "config"))

    def _tm_norm(path):
        # путь как в авто-списке: без store., кавычки двойные, без пробелов в []
        p = (path or "").strip()
        if p.startswith("store."):
            p = p[6:]
        p = p.replace("'", '"')
        return _tm_re.sub(r'\[\s*([^\]]*?)\s*\]', r'[\1]', p)

    def _tm_ctx_label(node):
        try:
            return tm_label_at(node.filename, node.linenumber)
        except Exception:
            return None

    def _tm_usage():
        # {путь: {"chg": [(вид, текст, где)], "chk": [(оп, число|None, где)], "nchg", "nchk",
        #  "choice": число изменений в выборах, "word": подпись из реплик}} — один раз за сессию
        u = renpy.session.get("tm_usage")
        if u is not None:
            return u
        u = {}
        nodes = _tm_script_nodes()
        own = lambda n: not (n.filename.startswith("renpy/common") or "zzz_testmenu" in n.filename
                             or n.filename.startswith("renpy/"))

        def rec(path):
            p = _tm_norm(path)
            r = u.get(p)
            if r is None:
                r = u[p] = {"chg": [], "chk": [], "nchg": 0, "nchk": 0, "choice": 0, "word": None}
            return r

        # 1) какие узлы лежат внутри варианта выбора -> текст варианта
        in_choice = {}

        def mark(block, text):
            for n in block or ():
                in_choice[id(n)] = text
                if isinstance(n, renpy.ast.Menu):
                    continue                # у вложенного выбора свои варианты
                if isinstance(n, renpy.ast.If):
                    for _c, b in n.entries:
                        mark(b, text)
                elif isinstance(n, renpy.ast.While):
                    mark(n.block, text)

        for n in nodes:
            try:
                if isinstance(n, renpy.ast.Menu) and own(n):
                    for item in n.items:
                        if item[2] is not None and item[0]:
                            mark(item[2], _tm_short(tm_choice_text(item[0]), 30))
            except Exception:
                continue

        def where(n):
            c = in_choice.get(id(n))
            if c:
                return u"«%s»" % c
            lab = _tm_ctx_label(n)
            return (u"сцена %s" % lab) if lab else u""

        def target_of(block):
            # куда ведёт ветка условия: первый jump/call в ней
            for b in block or ():
                if isinstance(b, renpy.ast.Jump) and not b.expression:
                    return u"сцена %s" % b.target
                if isinstance(b, renpy.ast.Call) and not b.expression:
                    return u"сцена %s" % b.label
            return None

        def checks(cond, ctx):
            if not cond or cond.strip() == "True":
                return
            found = set()
            for m in _TM_COND_NUM.finditer(cond):
                name, op, num = m.groups()
                r = rec(name)
                r["nchk"] += 1
                if len(r["chk"]) < 20:
                    r["chk"].append((op, float(num), ctx))
                found.add(_tm_norm(name))
            for m in _TM_COND_NUM_R.finditer(cond):
                num, op, name = m.groups()
                r = rec(name)
                r["nchk"] += 1
                if len(r["chk"]) < 20:
                    r["chk"].append((_TM_FLIP[op], float(num), ctx))
                found.add(_tm_norm(name))
            for m in _TM_COND_NAME.finditer(_tm_re.sub(r'"[^"]*"|\'[^\']*\'', "", cond)):
                name = m.group(1)
                if name in _TM_KEYWORDS or _tm_norm(name) in found or name.split(".")[0] in _TM_KEYWORDS:
                    continue
                r = rec(name)
                r["nchk"] += 1
                if len(r["chk"]) < 20:
                    r["chk"].append((None, None, ctx))

        for n in nodes:
            try:
                if not own(n):
                    continue
                if isinstance(n, renpy.ast.Python):
                    ctx = where(n)
                    for st in _tm_src_stmts(n.code.source):
                        if st.startswith(("if ", "elif ", "while ")):
                            checks(st.split(" ", 1)[1].rstrip(":"), ctx)
                            continue
                        m = _TM_ASSIGN_RE.match(st)
                        if not m:
                            continue
                        name, op, expr = m.groups()
                        r = rec(name)
                        r["nchg"] += 1
                        if id(n) in in_choice:
                            r["choice"] += 1
                        if len(r["chg"]) < 20:
                            r["chg"].append((op, _tm_short(expr, 16), ctx))
                elif isinstance(n, renpy.ast.If):
                    for cond, blk in n.entries:
                        checks(cond, target_of(blk) or where(n))
                elif isinstance(n, renpy.ast.While):
                    checks(n.condition, where(n))
                elif isinstance(n, renpy.ast.Menu):
                    for item in n.items:
                        if item[1] and item[0]:
                            checks(item[1], u"выбор «%s»" % _tm_short(tm_choice_text(item[0]), 30))
                elif isinstance(n, renpy.ast.Say):
                    w = n.what or ""
                    if "[" in w:
                        for m in _TM_SAY_AFTER.finditer(w):
                            r = rec(m.group(1))
                            r["word"] = r["word"] or m.group(2).lower()
                        for m in _TM_SAY_BEFORE.finditer(w):
                            r = rec(m.group(2))
                            r["word"] = r["word"] or m.group(1).lower()
            except Exception:
                continue
        renpy.session["tm_usage"] = u
        return u

    def tm_usage(path):
        return _tm_usage().get(_tm_norm(path))

    # ---------------- персонажи и подписи ----------------
    def _tm_chars():
        # {ключ в нижнем регистре: отображаемое имя}: имя персонажа и имя его переменной
        c = renpy.session.get("tm_chars")
        if c is not None:
            return c
        c = {}
        try:
            adv = renpy.character.ADVCharacter
            for var, v in vars(renpy.store).items():
                if not isinstance(var, _TM_STR) or var.startswith("_") or not isinstance(v, adv):
                    continue
                nm = getattr(v, "name", None)
                if not isinstance(nm, _TM_STR) or not nm.strip() or "[" in nm or "{" in nm:
                    continue
                nm = nm.strip()
                for key in (var.lower(), nm.lower(), nm.split()[0].lower()):
                    if len(key) >= 3:
                        c.setdefault(key, nm)
        except Exception:
            pass
        renpy.session["tm_chars"] = c
        return c

    def _tm_tokens(text):
        # «girls[Anna].loveLevel» -> [("girls", False), ("anna", True), ("love", False), ("level", False)]
        out = []
        for part in _tm_re.split(r'(\[[^\]]*\])', text or ""):
            if not part:
                continue
            is_key = part.startswith("[")
            s = part.strip("[]").strip('"\'')
            s = _tm_re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', s)
            for t in _tm_re.split(u'[^0-9A-Za-z\u00c0-\uffff]+', s):
                if t and (is_key or not t.isdigit()):    # flags[0] -> «Flags: 0»
                    out.append((t.lower(), is_key))
        return out

    def tm_word(tok):
        # перевод токена: точное слово, затем самое длинное слово-префикс (>= 4 букв, см. TM_INFLECT).
        # Меню на английском (13_lang.rpy) — слова имени остаются как есть: alice_love -> «Alice | Love»
        if tm_lang() == "en":
            return None
        w = TM_WORDS.get(tok)
        if w:
            return w
        best = None
        for k in TM_WORDS:
            if (len(k) >= 4 and tok.startswith(k) and (best is None or len(k) > len(best))
                    and (k in TM_STEMS or tok[len(k):] in TM_INFLECT)):
                best = k
        return TM_WORDS[best] if best else None

    def _tm_obj_name(path):
        # у объекта-владельца есть строковое поле name (anna.love -> Anna)
        # (re.split по пустому совпадению на py2 не режет — берём позиции «.» и «[»)
        cuts = [m.start() for m in _tm_re.finditer(r'[.\[]', path) if m.start() > 0]
        for i in reversed(cuts):
            owner = path[:i]
            try:
                o = renpy.python.py_eval(owner)
            except Exception:
                continue
            if _tm_plain_obj(o):
                nm = getattr(o, "name", None)
                if isinstance(nm, _TM_STR) and nm.strip() and len(nm) <= 30 and "[" not in nm:
                    return nm.strip()
        return None

    _TM_IDENT = _tm_re.compile(r"^[A-Za-z_][\w.\[\]\"']*$")
    _TM_EXPR = _tm_re.compile(r"[\s+\-*/%<>=!,]")       # оператор вне [...] — это выражение, не путь

    def _tm_user_names():
        n = renpy.session.get("tm_names")
        if n is not None:
            return n
        n = {}
        try:
            n.update(getattr(store.persistent, "tm_names", None) or {})
        except Exception:
            pass
        try:
            import json, io, os
            p = os.path.join(config.gamedir, "tm_names.json")
            if os.path.exists(p):
                with io.open(p, encoding="utf-8") as f:
                    d = json.load(f)
                if isinstance(d, _TM_DICT):
                    n.update(d)
        except Exception:
            pass
        renpy.session["tm_names"] = n
        return n

    def tm_nice(label, path):
        # -> (подпись, уверенно?) — для любого стата (кэш по пути)
        cache = renpy.session.get("tm_nice")
        if cache is None:
            cache = renpy.session["tm_nice"] = {}
        key = (label, path)
        if key in cache:
            return cache[key]
        user = _tm_user_names().get(path)
        if user:
            cache[key] = (user, True)
            return cache[key]
        if label and label != path and not _TM_IDENT.match(label):
            cache[key] = (label, True)      # подпись из студии/data уже человеческая
            return cache[key]
        if path and _TM_EXPR.search(_tm_re.sub(r'\[[^\]]*\]', "", path)):
            cache[key] = (label or path, True)  # выражение (HUD: money + hp) — как написано
            return cache[key]
        toks = _tm_tokens(label if label else path)
        chars = _tm_chars()
        who, who_at = None, -1
        for i, (t, _k) in enumerate(toks):
            if t in chars:
                who, who_at = chars[t], i
                break
        if who is None:
            who = _tm_obj_name(path)
            if who:
                low = who.lower()
                for i, (t, _k) in enumerate(toks):
                    if t == low or t == low.split()[0]:
                        who_at = i
                        break
        if who_at >= 0:
            # имя персонажа из подписи убираем; если оно ключ (girls[Anna].love) — и контейнер перед ним
            toks = (toks[who_at + 1:] if toks[who_at][1] else toks[:who_at] + toks[who_at + 1:])
        base, keys, sure = [], [], who is not None
        for t, is_key in toks:
            if t in TM_GENERIC and not is_key:
                continue
            w = tm_word(t)
            sure = sure or bool(w)
            (keys if is_key else base).append(w or t)
        title = u" ".join(base)
        kt = u" ".join(keys)
        title = (title + u": " + kt) if (title and kt) else (title or kt)
        if not sure:
            u = tm_usage(path)
            if u and u["word"]:
                title, sure = u["word"], True
        if not title:
            title = path
        title = title[:1].upper() + title[1:]
        text = (u"%s | %s" % (who, title)) if who else title
        cache[key] = (text, sure)
        return cache[key]

    # ---------------- «что это делает» и пороги ----------------
    _TM_OPS = {"+=": u"+", "-=": u"−", "*=": u"×", "/=": u"÷", "=": u"= "}

    def tm_thresholds(path):
        # числа, которых сценарий требует (>= N, > N, == N) — по возрастанию
        u = tm_usage(path)
        out = set()
        for op, num, _w in (u["chk"] if u else ()):
            if num is None:
                continue
            if op in (">=", "=="):
                out.add(num)
            elif op == ">":
                out.add(num + 1 if num == int(num) else num)
        return sorted(int(x) if x == int(x) else x for x in out)

    def tm_next_threshold(path, cur):
        try:
            return next((t for t in tm_thresholds(path) if t > cur), None)
        except Exception:
            return None

    def tm_meaning(path):
        # -> (короткая строка под именем, полный текст для подсказки)
        u = tm_usage(path)
        if not u or not (u["nchg"] or u["nchk"]):
            s = tm_tr(u"в сценарии не меняется и не проверяется")
            return s, s
        short, full = [], []
        if u["chg"]:
            ex = sorted(u["chg"], key=lambda c: not c[2].startswith(u"«"))
            parts = [u"%s%s %s" % (_TM_OPS.get(op, op), e, w) for op, e, w in ex[:2]]
            more = u["nchg"] - len(parts)
            short.append(tm_tr(u"меняется: ") + u", ".join(parts) + (tm_tr(u" и ещё %d") % more if more > 0 else u""))
            full.append(tm_tr(u"Меняется в %d местах: ") % u["nchg"]
                        + u"; ".join(u"%s%s %s" % (_TM_OPS.get(op, op), e, w) for op, e, w in ex[:6]))
        need = [(op, num, w) for op, num, w in u["chk"] if num is not None]
        if need:
            need.sort(key=lambda c: c[1])
            fmt = lambda c: u"%s %s → %s" % (c[0].replace(">=", u"≥").replace("<=", u"≤"),
                                              int(c[1]) if c[1] == int(c[1]) else c[1], c[2])
            short.append(tm_tr(u"нужно ") + fmt(need[0]))
            full.append(tm_tr(u"Проверяется: ") + u"; ".join(fmt(c) for c in need[:6]))
        elif u["nchk"]:
            w = u["chk"][0][2]
            short.append(tm_tr(u"проверяется") + (u": " + w if w else u""))
            full.append(tm_tr(u"Проверяется в %d условиях") % u["nchk"] + (tm_tr(u", например ") + w if w else u""))
        return u"; ".join(short), u". ".join(full)

    def tm_score(kind, path):
        # важность для сортировки: проверяется в условиях > меняется в выборах > меняется
        u = tm_usage(path)
        s = 0
        if u:
            s += 4 * min(u["nchk"], 3) + 3 * min(u["choice"], 3) + min(u["nchg"], 5)
        if kind == "num" and _tm_auto_score(path):
            s += 2
        return s

    def tm_group_of(kind, label, path):
        # группа строки авто-списка: персонаж / деньги / время / статы / флаги / строки / служебное
        toks = [t for t, _k in _tm_tokens(label or path)]
        nice, _sure = tm_nice(label, path)
        if u" | " in nice and kind in ("num", "flag"):
            return nice.split(u" | ")[0]
        u = tm_usage(path)
        used = bool(u and (u["nchg"] or u["nchk"]))
        if kind in ("num", "flag") and toks and toks[0] in TM_INV:
            return u"Инвентарь"
        if kind == "num":
            if any(t in TM_MONEY for t in toks):
                return u"Деньги"
            if any(t in TM_TIME for t in toks):
                return u"Время"
            if used or _tm_auto_score(path):
                return u"Статы"
        elif kind == "flag" and used:
            return u"Сюжетные флаги"
        elif kind == "str":
            return u"Строки"
        return u"Служебное"

    def tm_row_info(label, path):
        # (подпись, короткий смысл, полная подсказка) — для строки вкладки и «Поиска»
        nice, sure = tm_nice(label, path)
        short, full = tm_meaning(path)
        tip = full + (u"" if sure else u". Имя — догадка по названию переменной")
        return nice, short, tip + u". Щёлкни по имени, чтобы переименовать."

    def tm_set_name(path, raw):
        # своё имя переменной (пусто — вернуть автоматическое)
        raw = (raw or "").strip().replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")
        names = dict(_tm_user_names())
        if raw:
            names[path] = raw
        else:
            names.pop(path, None)
        # имена — в game/tm_names.json (их видит студия), запасной вариант — persistent
        try:
            import json, io, os
            with io.open(os.path.join(config.gamedir, "tm_names.json"), "w", encoding="utf-8") as f:
                f.write(tm_str(json.dumps(names, ensure_ascii=True, indent=1, sort_keys=True)))
        except Exception:
            store.persistent.tm_names = names
        renpy.session["tm_names"] = names
        renpy.session["tm_nice"] = None
        renpy.session["tm_auto"] = None
        renpy.restart_interaction()

    def tm_to_threshold(path, t):
        tm_set(path, t)

