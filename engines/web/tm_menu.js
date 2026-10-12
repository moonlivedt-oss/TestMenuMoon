/* Любая HTML5-игра — адаптер данных для общего UI-ядра (_shared/tm_menu_core.js).
   Переменных игры заранее не знаем, поэтому ищем их в рантайме:
     - Construct 2: глобальные переменные проекта (cr_getC2Runtime().all_global_vars);
     - Construct 3: глобальные переменные и переменные экземпляров (IRuntime; режим DOM
       или runtime, выставленный скриптом проекта — в режиме воркера недоступно);
     - GDevelop: переменные игры и текущей сцены (сцену ловим через renderAndStep);
     - Phaser 3: registry и data активных сцен;
     - остальное: глобалы страницы, которых нет в чистом window (сравнение с пустым
       iframe), и их поля на 3 уровня вглубь.
   Скорость игры — подменой времени в ядре (speed: true). */
var TMW = { base: null, gd: null, max: 900 };

// известные библиотеки: у них тысячи полей, а данных игры нет
var TMW_LIBS = { Phaser: 1, PIXI: 1, THREE: 1, BABYLON: 1, Howl: 1, Howler: 1, jQuery: 1, $: 1, _: 1,
  createjs: 1, Matter: 1, p2: 1, Box2D: 1, CANNON: 1, gdjs: 1, localforage: 1, Module: 1, React: 1,
  ReactDOM: 1, Vue: 1, webpackJsonp: 1, regeneratorRuntime: 1, Stats: 1, dat: 1, gsap: 1, TweenMax: 1,
  TweenLite: 1, TimelineMax: 1, Hammer: 1, io: 1, firebase: 1, gtag: 1, dataLayer: 1, ga: 1,
  TM_ADAPTER: 1, TM_ICONS: 1, TMW: 1, TMW_LIBS: 1, TMW_WORDS: 1, __TM_MENU__: 1 };

// слова статов: группы с ними поднимаются наверх
var TMW_WORDS = /(hp|health|life|lives|mana|mp|energy|stamina|gold|coin|money|cash|gem|score|level|lvl|xp|exp|ammo|bullet|damage|attack|defen[cs]e|armor|speed|power|strength|luck|key|item|potion|time|wave|kill|point|stage|day|hunger|thirst|karma|rep|love|affection|trust)/i;

function tmwBaseline() {
  if (TMW.base) return TMW.base;
  var b = {};
  try {
    var f = document.createElement("iframe");
    f.style.display = "none";
    document.documentElement.appendChild(f);
    Object.getOwnPropertyNames(f.contentWindow).forEach(function (k) { b[k] = 1; });
    f.remove();
  } catch (e) {}
  TMW.base = b;
  return b;
}

// --- «где меняется»: на время слежки свойство становится аксессором, и каждая запись
// запоминает стек вызова. Итог — функции игры, которые пишут это значение, и сколько раз.
var TMW_WATCH_MS = 15000;
function tmwWatch(owner, key, name, cb) {
  var d;
  try { d = Object.getOwnPropertyDescriptor(owner, key); } catch (e) {}
  if (!d || !("value" in d) || !d.configurable) {
    cb(["Это значение не отследить: свойство нельзя перенастроить (var на странице, " +
        "замороженный объект или геттер движка). Попробуй поле объекта уровнем ниже."]);
    return;
  }
  var value = d.value, hits = {}, total = 0, prog = "", seen = 0;
  Object.defineProperty(owner, key, {
    configurable: true, enumerable: d.enumerable,
    get: function () { return value; },
    set: function (v) {
      if (v !== value) {
        total++;
        var st = String((new Error()).stack || "").split("\n").slice(2)
          .filter(function (l) { return l.indexOf("tmwWatch") < 0 && /\S/.test(l); })
          .slice(0, 3).map(function (l) { return l.trim().replace(/^at /, ""); }).join("  <-  ");
        if (!hits[st]) { hits[st] = { n: 0, from: value, to: v }; seen++; }
        hits[st].n++; hits[st].to = v;
      }
      value = v;
    }
  });
  setTimeout(function () {
    try { Object.defineProperty(owner, key, { configurable: true, enumerable: d.enumerable, writable: true, value: value }); } catch (e) {}
    var lines = ["Слежка " + TMW_WATCH_MS / 1000 + " с: изменений " + total + ", мест в коде " + seen + "."];
    Object.keys(hits).sort(function (a, b) { return hits[b].n - hits[a].n; }).slice(0, 12).forEach(function (st) {
      var h = hits[st];
      lines.push("×" + h.n + "  (" + h.from + " → " + h.to + ")  " + (st || "без стека (изменилось из встроенного кода)"));
    });
    if (!total) lines.push("Игра не меняла значение. Сделай в игре то, что должно его менять, и запусти снова.");
    cb(lines);
  }, TMW_WATCH_MS);
}
function tmwRow(owner, key, name, type) {
  return { name: name, type: type,
    get: function () { return owner[key]; },
    set: function (x) { owner[key] = x; },
    where: function (cb) { tmwWatch(owner, key, name, cb); } };
}

function tmwType(v) {
  var t = typeof v;
  if (t === "number") return isFinite(v) ? "num" : null;
  if (t === "boolean") return "bool";
  if (t === "string") return v.length <= 200 ? "str" : null;
  return null;
}

function tmwSkipObj(v) {
  if (!v || typeof v !== "object") return true;
  if (typeof Node !== "undefined" && v instanceof Node) return true;
  if (v === window || ArrayBuffer.isView(v) || v instanceof ArrayBuffer) return true;
  if (typeof CanvasRenderingContext2D !== "undefined" && v instanceof CanvasRenderingContext2D) return true;
  if (typeof WebGLRenderingContext !== "undefined" && v instanceof WebGLRenderingContext) return true;
  if (v instanceof Promise || v instanceof RegExp || v instanceof Date) return true;
  return false;
}

// поля объекта (и вложенных) как строки «путь = значение»
function tmwWalk(obj, path, depth, out, seen) {
  if (out.length >= TMW.max || tmwSkipObj(obj) || seen.indexOf(obj) >= 0) return;
  seen.push(obj);
  var keys;
  try { keys = Array.isArray(obj) ? (obj.length <= 64 ? Object.keys(obj) : []) : Object.keys(obj); } catch (e) { return; }
  if (keys.length > 300) return;  // словари-кэши и таблицы ассетов
  keys.forEach(function (k) {
    if (out.length >= TMW.max) return;
    var v;
    try { v = obj[k]; } catch (e) { return; }
    var name = Array.isArray(obj) ? path + "[" + k + "]" : (path ? path + "." + k : k);
    var t = tmwType(v);
    if (t) {
      out.push(tmwRow(obj, k, name, t));
    } else if (depth > 0 && v && typeof v === "object") {
      tmwWalk(v, name, depth - 1, out, seen);
    }
  });
}

function tmwScore(rows) {
  var n = 0;
  rows.forEach(function (r) { if (TMW_WORDS.test(r.name.split(/[.\[]/).pop())) n++; });
  return n;
}

// --- Construct 2
function tmwConstruct2(secs) {
  if (typeof cr_getC2Runtime !== "function") return;
  var rt; try { rt = cr_getC2Runtime(); } catch (e) { return; }
  var gv = (rt && rt.all_global_vars) || [], rows = [];
  gv.forEach(function (v) {
    var t = tmwType(v.data);
    if (t) rows.push(tmwRow(v, "data", v.name, t));
  });
  if (rows.length) secs.push({ title: "Construct 2: глобальные переменные", rows: rows, top: true });
}

// --- Construct 3: IRuntime — из скрипта проекта (globalThis.runtime, частый приём
// runOnStartup) или у рантайма в режиме DOM (c3_runtimeInterface._localRuntime).
// В режиме воркера (по умолчанию в новых проектах) рантайм в другом потоке — недоступен.
function tmwC3Runtime() {
  var cands = [window.runtime, window.c3runtime, window.gameRuntime];
  for (var i = 0; i < cands.length; i++) if (cands[i] && cands[i].globalVars && cands[i].objects) return cands[i];
  var ri = window.c3_runtimeInterface;
  if (!ri) return null;
  try {
    var rt = ri._localRuntime || (ri._GetLocalRuntime && ri._GetLocalRuntime());
    return rt && rt.GetIRuntime ? rt.GetIRuntime() : null;
  } catch (e) { return null; }
}
function tmwConstruct3(secs) {
  var ir = tmwC3Runtime();
  if (!ir) {
    if (window.c3_runtimeInterface) TMW.c3worker = true;
    return;
  }
  var gv = ir.globalVars, rows = [];
  if (gv) Object.getOwnPropertyNames(gv).forEach(function (k) {
    var t;
    try { t = tmwType(gv[k]); } catch (e) { return; }
    if (t) rows.push({ name: k, type: t, get: function () { return gv[k]; }, set: function (x) { gv[k] = x; } });
  });
  if (rows.length) secs.push({ title: "Construct 3: глобальные переменные", rows: rows, top: true });
  var objs = ir.objects, inst = [];
  if (objs) Object.keys(objs).slice(0, 60).forEach(function (type) {
    var list;
    try { list = objs[type].getAllInstances(); } catch (e) { return; }
    (list || []).slice(0, 4).forEach(function (o, n) {
      var iv = o && o.instVars;
      if (!iv) return;
      Object.getOwnPropertyNames(iv).forEach(function (k) {
        var t;
        try { t = tmwType(iv[k]); } catch (e) { return; }
        if (t) inst.push({ name: type + (list.length > 1 ? "#" + n : "") + "." + k, type: t,
          get: function () { return iv[k]; }, set: function (x) { iv[k] = x; } });
      });
    });
  });
  if (inst.length) secs.push({ title: "Construct 3: переменные экземпляров", rows: inst, top: true });
}

// --- GDevelop: сцену ловим на ходу (renderAndStep зовётся каждый кадр)
function tmwGdHook() {
  if (TMW.gdHooked || typeof gdjs === "undefined" || !gdjs.RuntimeScene) return;
  TMW.gdHooked = true;
  var p = gdjs.RuntimeScene.prototype, orig = p.renderAndStep;
  if (orig) p.renderAndStep = function () { TMW.gd = this; return orig.apply(this, arguments); };
}
function tmwGdVars(container, title, secs) {
  var items = container && container._variables && (container._variables.items || container._variables);
  if (!items) return;
  var rows = [];
  function add(name, v) {
    var t = v.getType ? v.getType() : (typeof v.getValue() === "number" ? "number" : "string");
    if (t === "number") rows.push({ name: name, type: "num", get: function () { return v.getAsNumber ? v.getAsNumber() : v.getValue(); }, set: function (x) { v.setNumber(x); } });
    else if (t === "boolean") rows.push({ name: name, type: "bool", get: function () { return v.getAsBoolean(); }, set: function (x) { v.setBoolean(x); } });
    else if (t === "string") rows.push({ name: name, type: "str", get: function () { return v.getAsString(); }, set: function (x) { v.setString(x); } });
    else if ((t === "structure" || t === "array") && v.getAllChildren) {
      var ch = v.getAllChildren();
      Object.keys(ch).slice(0, 100).forEach(function (k) { add(name + "." + k, ch[k]); });
    }
  }
  Object.keys(items).forEach(function (k) { try { add(k, items[k]); } catch (e) {} });
  if (rows.length) secs.push({ title: title, rows: rows, top: true });
}
function tmwGdevelop(secs) {
  tmwGdHook();
  var sc = TMW.gd;
  if (!sc) return;
  try { tmwGdVars(sc.getGame().getVariables(), "GDevelop: переменные игры", secs); } catch (e) {}
  try { tmwGdVars(sc.getVariables(), "GDevelop: переменные сцены", secs); } catch (e) {}
}

// --- Phaser 3: registry игры и data сцен (сам объект игры не обходим — там движок)
function tmwIsPhaserGame(v) { return v && typeof v === "object" && v.registry && v.scene && v.renderer && v.loop; }
function tmwPhaser(game, gname, secs) {
  function dm(list, title) {
    var rows = [];
    Object.keys(list || {}).forEach(function (k) {
      var t = tmwType(list[k]);
      if (t) rows.push(tmwRow(list, k, k, t));
    });
    if (rows.length) secs.push({ title: title, rows: rows, top: true });
  }
  dm(game.registry.list, "Phaser: registry (" + gname + ")");
  (game.scene.scenes || []).forEach(function (s) {
    if (!s.sys || !s.sys.isActive || !s.sys.isActive()) return;
    var key = (s.sys.settings && s.sys.settings.key) || "scene";
    if (s.data) dm(s.data.list, "Phaser: сцена " + key + " (data)");
    var own = [];
    tmwWalk(s, "", 1, own, [s.sys, s.game, s.add, s.make, s.cameras, s.input, s.load, s.physics, s.tweens, s.time,
      s.anims, s.sound, s.textures, s.events, s.registry, s.data, s.children, s.lights, s.scale, s.plugins, s.renderer]);
    own = own.filter(function (r) { return r.name.indexOf("sys.") !== 0; });
    if (own.length) secs.push({ title: "Phaser: сцена " + key + " (поля)", rows: own, top: true });
  });
}

function tmwScan() {
  var secs = [], base = tmwBaseline(), globals = [];
  tmwConstruct2(secs);
  tmwConstruct3(secs);
  tmwGdevelop(secs);
  var objs = [];
  Object.getOwnPropertyNames(window).forEach(function (k) {
    if (base[k] || TMW_LIBS[k] || /^(on|webkit|moz|cr_|c2|c3|C3|__|tm)/.test(k)) return;
    var v;
    try { v = window[k]; } catch (e) { return; }
    if (typeof v === "function") return;
    var t = tmwType(v);
    if (t) {
      globals.push(tmwRow(window, k, k, t));
      return;
    }
    if (tmwIsPhaserGame(v)) { tmwPhaser(v, k, secs); return; }
    if (v && typeof v === "object" && !tmwSkipObj(v)) objs.push(k);
  });
  if (globals.length) secs.push({ title: "Глобальные переменные", rows: globals, top: true });
  if (TMW.c3worker && !secs.some(function (s) { return /Construct 3/.test(s.title); }))
    secs.unshift({ title: "Construct 3: рантайм в воркере — переменные игры недоступны (видно только страницу)", rows: [] });
  var groups = [];
  objs.forEach(function (k) {
    var rows = [];
    tmwWalk(window[k], k, 2, rows, []);
    if (rows.length) groups.push({ title: k, rows: rows, score: tmwScore(rows) });
  });
  // группы со словами-статами — выше, внутри одного веса — меньшие (там меньше шума)
  groups.sort(function (a, b) { return (b.score - a.score) || (a.rows.length - b.rows.length); });
  return secs.concat(groups);
}

window.TM_ADAPTER = {
  accent: "#7cc4ff",
  title: "HTML5-игра",
  ready: function () { return !!document.body; },

  stats: function () { return tmwScan(); },

  whereHint: "Слежу 15 с: закрой меню и сделай в игре то, что меняет значение",
  whereTip: "Кто в коде игры меняет это значение: 15 секунд слежки за записью, потом список мест",

  nums: function () {
    var o = {};
    tmwScan().forEach(function (s) {
      s.rows.forEach(function (r) { if (r.type === "num") { try { o[s.title + " / " + r.name] = r.get(); } catch (e) {} } });
    });
    return o;
  },

  speed: true,

  actions: function () {
    return [
      { label: "Пересканировать", desc: "заново найти объекты игры (после загрузки уровня)", run: function () { TMW.base = null; } },
      { label: "Найденное → в консоль", desc: "F12 → Console: группы и пути", run: function () {
        tmwScan().forEach(function (s) { console.log("[TM]", s.title, s.rows.map(function (r) { return r.name; })); });
      } },
      { label: "Своя команда (JS)…", desc: "выполняется в странице игры", run: function () { var c = prompt("JS:", "score = 1000"); if (c) (0, eval)(c); } }
    ];
  },

  footMissing: "Страница ещё не загрузилась — открой меню, когда игра появится."
};
