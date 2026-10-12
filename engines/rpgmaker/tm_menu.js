/* RPG Maker MV/MZ — адаптер данных для общего UI-ядра (_shared/tm_menu_core.js).
   Инжектор склеивает этот адаптер + ядро в один <script>.
   Глобалы игры проверяем через typeof, а не window.X: в MZ они объявлены через let
   и свойствами window не являются (в MV — var, там работало и так). */
function tmHas(name) {
  try { var v = (0, eval)(name); return typeof v !== "undefined" && v !== null; } catch (e) { return false; }
}

// Режимы и скорость: правки прототипов игры ставятся один раз и сами смотрят на флаги
// TMR, поэтому выключение режима возвращает поведение игры без снятия патчей.
var TMR = window.TM_RPGM = { speed: 1, acc: 0, through: false, noenc: false, god: false, freemp: false, exp: false, clicktp: false };
function tmrPatch() {
  if (TMR.patched || !tmHas("Game_Player") || !tmHas("Game_Actor")) return;
  TMR.patched = true;
  var P = Game_Player.prototype, AP = Game_Actor.prototype;
  // isDebugThrough — штатный проход сквозь стены движка (Ctrl в тест-запуске)
  var dbg = P.isDebugThrough;
  P.isDebugThrough = function () { return TMR.through || dbg.call(this); };
  var enc = P.canEncounter;
  P.canEncounter = function () { return !TMR.noenc && enc.call(this); };
  var setHp = AP.setHp;
  AP.setHp = function (hp) { if (TMR.god && hp < this.hp) hp = this.hp; return setHp.call(this, hp); };
  var addState = AP.addState;
  AP.addState = function (id) { if (TMR.god && id === this.deathStateId()) return; return addState.call(this, id); };
  var mp = AP.skillMpCost, tp = AP.skillTpCost;
  AP.skillMpCost = function (s) { return TMR.freemp ? 0 : mp.call(this, s); };
  AP.skillTpCost = function (s) { return TMR.freemp ? 0 : tp.call(this, s); };
  var touch = tmHas("Scene_Map") && Scene_Map.prototype.processMapTouch;
  if (touch) Scene_Map.prototype.processMapTouch = function () {
    if (TMR.clicktp && TouchInput.isTriggered() && $gamePlayer.canMove()) {
      $gamePlayer.locate($gameMap.canvasToMapX(TouchInput.x), $gameMap.canvasToMapY(TouchInput.y));
      $gameTemp.clearDestination();
      return;
    }
    return touch.apply(this, arguments);
  };
  var rate = AP.finalExpRate;
  AP.finalExpRate = function () { return rate.call(this) * (TMR.exp ? 10 : 1); };
}
function tmrCheat(key, label, desc) {
  return { label: label, desc: desc, get: function () { return TMR[key]; }, set: function (v) { tmrPatch(); TMR[key] = v; } };
}

// ---- индекс данных игры: все карты, общие события, отряды врагов.
// Кто меняет / проверяет переключатель или переменную, входы на каждую карту.
// Карты грузятся один раз, асинхронно (те же data/MapNNN.json, что читает игра).
var TMR_OPS = ["=", "+=", "-=", "*=", "/=", "%="], TMR_CMP = ["=", ">=", "<=", ">", "<", "!="];
function tmrPad(n) { return ("00" + n).slice(-3); }
function tmrMapName(id) { var i = tmHas("$dataMapInfos") && $dataMapInfos[id]; return (i && i.name) || "Карта " + id; }
function tmrLoad(cb) {
  if (TMR.idx) { cb(TMR.idx); return; }
  (TMR.waiters = TMR.waiters || []).push(cb);
  if (TMR.loading) return;
  TMR.loading = true;
  var ids = [], maps = {};
  (tmHas("$dataMapInfos") ? $dataMapInfos : []).forEach(function (m) { if (m) ids.push(m.id); });
  var left = ids.length;
  function done() { TMR.idx = tmrIndex(maps); TMR.loading = false; TMR.waiters.splice(0).forEach(function (w) { w(TMR.idx); }); }
  if (!left) { done(); return; }
  ids.forEach(function (id) {
    var x = new XMLHttpRequest();
    x.open("GET", "data/Map" + tmrPad(id) + ".json");
    x.onload = x.onerror = function () {
      try { if (x.status < 400 && x.responseText) maps[id] = JSON.parse(x.responseText); } catch (e) {}
      if (--left === 0) done();
    };
    x.send();
  });
}
function tmrIndex(maps) {
  var idx = { sw: {}, "var": {}, enter: {}, maps: maps };
  function put(kind, id, where, what) { (idx[kind][id] = idx[kind][id] || []).push(where + ": " + what); }
  function scan(list, where) {
    (list || []).forEach(function (c) {
      var p = c.parameters || [];
      if (c.code === 121) for (var i = p[0]; i <= p[1]; i++) put("sw", i, where, p[2] === 0 ? "включает" : "выключает");
      else if (c.code === 122) {
        var src = p[3] === 0 ? String(p[4]) : p[3] === 1 ? "#" + p[4] : p[3] === 2 ? "случайно " + p[4] + "…" + p[5] : p[3] === 4 ? "скрипт" : "данные игры";
        for (var j = p[0]; j <= p[1]; j++) put("var", j, where, TMR_OPS[p[2]] + " " + src);
      } else if (c.code === 111 && p[0] === 0) put("sw", p[1], where, "условие: " + (p[2] === 0 ? "ВКЛ" : "выкл"));
      else if (c.code === 111 && p[0] === 1) put("var", p[1], where, "условие: " + TMR_CMP[p[4]] + " " + (p[2] === 0 ? p[3] : "#" + p[3]));
      else if (c.code === 201 && p[0] === 0) (idx.enter[p[1]] = idx.enter[p[1]] || []).push({ x: p[2], y: p[3], from: where });
    });
  }
  function pageCond(cn, where) {
    if (!cn) return;
    if (cn.switch1Valid) put("sw", cn.switch1Id, where, "условие страницы: ВКЛ");
    if (cn.switch2Valid) put("sw", cn.switch2Id, where, "условие страницы: ВКЛ");
    if (cn.variableValid) put("var", cn.variableId, where, "условие страницы: >= " + cn.variableValue);
    if (cn.switchValid) put("sw", cn.switchId, where, "условие: ВКЛ");
  }
  Object.keys(maps).forEach(function (id) {
    (maps[id].events || []).forEach(function (ev) {
      if (!ev) return;
      (ev.pages || []).forEach(function (pg, k) {
        var w = tmrMapName(id) + ", событие «" + ev.name + "» (" + ev.x + ", " + ev.y + "), стр. " + (k + 1);
        pageCond(pg.conditions, w);
        scan(pg.list, w);
      });
    });
  });
  (tmHas("$dataCommonEvents") ? $dataCommonEvents : []).forEach(function (ce) {
    if (!ce) return;
    var w = "Общее событие «" + ce.name + "»";
    if (ce.trigger > 0) put("sw", ce.switchId, w, "запуск при ВКЛ");
    scan(ce.list, w);
  });
  (tmHas("$dataTroops") ? $dataTroops : []).forEach(function (t) {
    if (!t) return;
    (t.pages || []).forEach(function (pg, k) { var w = "Бой «" + t.name + "», стр. " + (k + 1); pageCond(pg.conditions, w); scan(pg.list, w); });
  });
  if (tmHas("$dataSystem") && $dataSystem.startMapId)
    (idx.enter[$dataSystem.startMapId] = idx.enter[$dataSystem.startMapId] || []).unshift({ x: $dataSystem.startX, y: $dataSystem.startY, from: "старт игры" });
  return idx;
}
function tmrWhere(kind, id, cb) {
  tmrLoad(function (idx) { cb(idx[kind][id] || ["Нигде в событиях не встречается (может меняться скриптом плагина)."]); });
}
// вход на карту: старт игры или первый перенос сюда; иначе — середина карты
function tmrEntry(idx, id) {
  var e = idx.enter[id];
  if (e && e.length) return e[0];
  var m = idx.maps[id];
  return m ? { x: Math.floor(m.width / 2), y: Math.floor(m.height / 2), from: "середина карты" } : null;
}

window.TM_ADAPTER = {
  accent: "#ff9f43",
  title: "RPG Maker MV/MZ",
  ready: function () { return tmHas("$gameVariables") && tmHas("$dataSystem"); },

  stats: function () {
    if (!this.ready()) return [];
    var secs = [];
    if (tmHas("$gameParty")) secs.push({ title: "Деньги", rows: [{
      name: "Золото", type: "num",
      get: function () { return $gameParty.gold(); },
      set: function (v) { var d = v - $gameParty.gold(); if (d >= 0) $gameParty.gainGold(d); else $gameParty.loseGold(-d); }
    }] });

    var vn = $dataSystem.variables || [], vr = [];
    for (var i = 1; i < vn.length; i++) {
      if (!vn[i]) continue;
      (function (id, nm) {
        vr.push({ name: nm + "  #" + id, type: "num",
          get: function () { return $gameVariables.value(id); },
          set: function (v) { $gameVariables.setValue(id, v); },
          where: function (cb) { tmrWhere("var", id, cb); } });
      })(i, vn[i]);
    }
    if (vr.length) secs.push({ title: "Переменные", rows: vr });

    // отряд: уровень, HP/MP/TP, опыт и базовые параметры каждого героя
    if (tmHas("$gameParty") && $gameParty.members) $gameParty.members().forEach(function (a) {
      var rows = [
        { name: "Уровень", type: "num", get: function () { return a.level; }, set: function (v) { a.changeLevel(Math.max(1, Math.round(v)), false); } },
        { name: "HP", type: "num", get: function () { return a.hp; }, set: function (v) { a.setHp(v); } },
        { name: "MP", type: "num", get: function () { return a.mp; }, set: function (v) { a.setMp(v); } },
        { name: "TP", type: "num", get: function () { return a.tp; }, set: function (v) { a.setTp(v); } },
        { name: "Опыт", type: "num", get: function () { return a.currentExp(); }, set: function (v) { a.changeExp(Math.max(0, v), false); } }
      ];
      for (var pid = 0; pid < 8; pid++) (function (id) {
        var nm = tmHas("TextManager") && TextManager.param ? TextManager.param(id) : "param " + id;
        rows.push({ name: nm, type: "num", get: function () { return a.param(id); }, set: function (v) { a.addParam(id, v - a.param(id)); } });
      })(pid);
      secs.push({ title: "Отряд: " + a.name(), rows: rows });
    });

    var sn = $dataSystem.switches || [], sr = [];
    for (var j = 1; j < sn.length; j++) {
      if (!sn[j]) continue;
      (function (id, nm) {
        sr.push({ name: nm + "  #" + id, type: "bool",
          get: function () { return $gameSwitches.value(id); },
          set: function (v) { $gameSwitches.setValue(id, v); },
          where: function (cb) { tmrWhere("sw", id, cb); } });
      })(j, sn[j]);
    }
    if (sr.length) secs.push({ title: "Переключатели", rows: sr });

    // инвентарь: количество правится через gainItem (он сам держит 0..макс)
    function items(title, global) {
      if (!tmHas(global) || !tmHas("$gameParty") || !$gameParty.numItems) return;
      var data = (0, eval)(global), rows = [];
      for (var k = 1; k < data.length; k++) {
        if (!data[k] || !data[k].name) continue;
        (function (it) {
          rows.push({ name: it.name + "  #" + it.id, type: "num",
            get: function () { return $gameParty.numItems(it); },
            set: function (v) { $gameParty.gainItem(it, v - $gameParty.numItems(it)); } });
        })(data[k]);
      }
      if (rows.length) secs.push({ title: title, rows: rows });
    }
    items("Предметы", "$dataItems");
    items("Оружие", "$dataWeapons");
    items("Броня", "$dataArmors");
    return secs;
  },

  nums: function () {
    var o = {};
    if (!this.ready()) return o;
    if (tmHas("$gameParty")) o["Золото"] = $gameParty.gold();
    var vn = $dataSystem.variables || [];
    for (var i = 1; i < vn.length; i++) if (vn[i]) o["#" + i + " " + vn[i]] = $gameVariables.value(i);
    return o;
  },

  actions: function () {
    return [
      { label: "Золото +99999", run: function () { $gameParty.gainGold(99999); } },
      { label: "Лечить отряд", run: function () { ($gameParty.members ? $gameParty.members() : []).forEach(function (a) { if (a.recoverAll) a.recoverAll(); }); } },
      { label: "Победа в бою", desc: "все враги падают, бой закончится сам", run: function () {
        if (!$gameParty.inBattle()) throw new Error("не в бою");
        $gameTroop.members().forEach(function (e) { e.addState(e.deathStateId()); e.refresh(); });
      } },
      { label: "Сбежать из боя", run: function () { if (!$gameParty.inBattle()) throw new Error("не в бою"); BattleManager.processAbort(); } },
      { label: "Окно сохранения", desc: "сохраниться где угодно, даже если игра запретила", run: function () { $gameSystem.enableSave(); SceneManager.push(Scene_Save); } },
      { label: "Окно загрузки", run: function () { SceneManager.push(Scene_Load); } },
      { label: "Телепорт на карту…", desc: "ID карты, x, y", run: function () {
        var c = prompt("ID карты, x, y:", $gameMap.mapId() + ", " + $gamePlayer.x + ", " + $gamePlayer.y);
        if (!c) return;
        var n = c.split(/[\s,;]+/).map(Number);
        if (n.length < 3 || n.some(isNaN)) throw new Error("нужно три числа");
        $gamePlayer.reserveTransfer(n[0], n[1], n[2], $gamePlayer.direction(), 0);
      } },
      { label: "Все переключатели = ВКЛ", run: function () { var sn = $dataSystem.switches || []; for (var j = 1; j < sn.length; j++) if (sn[j]) $gameSwitches.setValue(j, true); } },
      { label: "Своя команда (JS)…", desc: "$gameParty/$gameVariables доступны", run: function () { var c = prompt("JS:", "$gameParty.gainGold(1000)"); if (c) (0, eval)(c); } }
    ];
  },

  // MV: кадры набираются по SceneManager._deltaTime; MZ: число обновлений за кадр
  // считает determineRepeatNumber — его результат умножаем (дробный остаток копится)
  speed: function (k) {
    if (!tmHas("SceneManager")) throw new Error("нет SceneManager");
    TMR.speed = k;
    if (SceneManager.determineRepeatNumber) {
      if (!SceneManager._tmDrn) {
        var orig = SceneManager._tmDrn = SceneManager.determineRepeatNumber;
        SceneManager.determineRepeatNumber = function (dt) {
          var n = orig.call(this, dt) * TMR.speed + TMR.acc, w = Math.min(Math.floor(n), 30);
          TMR.acc = TMR.speed ? n - Math.floor(n) : 0;
          return w;
        };
      }
    } else {
      if (SceneManager._tmDelta == null) SceneManager._tmDelta = SceneManager._deltaTime;
      SceneManager._deltaTime = k ? SceneManager._tmDelta / k : 1e9;
      SceneManager._accumulator = 0;  // иначе после паузы игра догоняет накопленное
    }
  },

  // шаг кадра на паузе: MZ — одно обновление в determineRepeatNumber, MV — накопитель на кадр
  step: function () {
    if (!tmHas("SceneManager")) throw new Error("нет SceneManager");
    if (SceneManager.determineRepeatNumber) TMR.acc += 1;
    else SceneManager._accumulator = SceneManager._deltaTime;
  },

  cheats: function () {
    if (!tmHas("Game_Player")) return [];
    return [
      tmrCheat("through", "Сквозь стены", "герой проходит через стены и события"),
      tmrCheat("noenc", "Без случайных боёв", "случайные встречи на карте отключены"),
      tmrCheat("god", "Бессмертие отряда", "HP героев не уменьшается, смерть не накладывается"),
      tmrCheat("freemp", "Навыки без затрат", "MP и TP на навыки не тратятся"),
      tmrCheat("exp", "Опыт ×10", "за бои героям идёт в 10 раз больше опыта"),
      tmrCheat("clicktp", "Телепорт по щелчку", "щелчок по клетке карты — герой сразу там (вместо хождения)")
    ];
  },

  // список карт для вкладки «Игра»: переход на вход карты (старт игры / первый перенос сюда)
  jumps: {
    title: "Карты",
    load: function (cb) {
      tmrLoad(function (idx) {
        var out = [];
        ($dataMapInfos || []).forEach(function (m) {
          if (!m) return;
          var e = tmrEntry(idx, m.id);
          if (!e) return;
          out.push({ name: tmrMapName(m.id) + "  #" + m.id, hint: "вход: " + e.from + " (" + e.x + ", " + e.y + ")",
            go: function () { $gamePlayer.reserveTransfer(m.id, e.x, e.y, $gamePlayer.direction(), 0); } });
        });
        cb(out);
      });
    }
  },

  places: {
    here: function () {
      if (!tmHas("$gameMap") || !$gameMap.mapId()) return null;
      var id = $gameMap.mapId(), info = tmHas("$dataMapInfos") && $dataMapInfos[id];
      return { map: id, x: $gamePlayer.x, y: $gamePlayer.y, d: $gamePlayer.direction(),
               name: ((info && info.name) || "Карта " + id) + "  (" + $gamePlayer.x + ", " + $gamePlayer.y + ")" };
    },
    go: function (p) { $gamePlayer.reserveTransfer(p.map, p.x, p.y, p.d || 2, 0); }
  },

  // пока меню открыто, keyup/mouseup до игры не доходят — сбрасываем «залипшие» клавиши
  onClose: function () {
    if (tmHas("Input") && Input.clear) Input.clear();
    if (tmHas("TouchInput") && TouchInput.clear) TouchInput.clear();
  },

  footMissing: "RPG Maker не обнаружен ($gameVariables нет) — открой в запущенной игре."
};
