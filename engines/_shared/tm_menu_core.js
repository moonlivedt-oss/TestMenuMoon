/* ============================================================================
 *  UNIVERSAL TEST MENU — общий UI-ядро (движко-независимое).
 *  Читает window.TM_ADAPTER (задаётся адаптером конкретного движка) и рисует
 *  оверлей: вкладки Значения / Игра / Сканер / Сейвы / Экшены, перетаскивание, тосты.
 *
 *  Контракт адаптера TM_ADAPTER:
 *    accent   : "#rrggbb"
 *    title    : "Название движка"   (id — ключ для localStorage, если title переводится)
 *    ready()  : bool — доступны ли данные игры
 *    stats()  : [ { title, rows:[ { name, type:'num'|'bool'|'str', get(), set(v) } ] } ]
 *    nums()   : { имя: число }              — числа для сканера
 *    actions(): [ { label, desc?, run() } ] — кнопки-экшены
 *    footMissing : строка для футера, когда ready()===false
 *    onClose()? : вызывается при закрытии меню (сбросить «залипший» ввод игры)
 *  Необязательное — вкладка «Игра» (появляется, если есть хоть что-то из этого):
 *    speed    : true — скорость игры через подмену времени (performance.now, Date.now,
 *               requestAnimationFrame); function(k) — своя реализация движка (k = 0 — пауза)
 *    step()?  : шаг одного кадра на паузе для своей реализации speed (у speed: true — сам)
 *    cheats() : [ { label, desc?, get(), set(bool) } ] — режимы-переключатели
 *    places   : { here(): {name, ...} | null, go(p) } — точки телепорта (хранятся в localStorage)
 *    jumps    : { title, load(cb) } — cb([{ name, hint?, go() }]): список мест для перехода (карты)
 *  У строки «Значений» может быть where(cb) — cb([строки]): где игра меняет и проверяет значение
 *  (ответ может прийти и при закрытом меню — покажется при следующем открытии);
 *  whereHint / whereTip — свой текст тоста и подсказки кнопки «где».
 * ==========================================================================*/
(function () {
  if (window.__TM_MENU__) return;
  // язык: tm_lang.js (TM_EN, T); без него — русский как есть
  if (typeof T !== "function") { window.T = function (s) { return s; }; window.TM_LANG = "ru"; window.tmSetLang = function () {}; }
  var A = window.TM_ADAPTER;
  if (!A) { console.warn(T("[TM] нет TM_ADAPTER — ядро меню не запущено")); return; }
  window.__TM_MENU__ = true;

  var K = window.TM_TOK;  // цвета и размеры: tm_tokens.js (tools/gen_tokens.py)
  var ACCENT = A.accent || K.accent;
  var step = 1, tab = "vals";
  var overlay = null, winEl = null, bodyEl = null;
  var scanSnap = {}, scanCands = null, scanMsg = T("Нажми «Снимок», измени что-то в игре, затем сужай.");
  var filter = "", winPos = null;
  // «живые» значения: пока меню открыто, показанные числа догоняют игру (таймеры,
  // события) без переоткрытия; frozen — заморозка: имя строки -> удерживаемое значение
  var live = [], liveTimer = null, frozen = {};

  // --- запоминание шага/вкладки/позиции окна между открытиями ---
  var LSKEY = "tm_menu_" + (A.id || A.title || "x");
  function saveState() { try { localStorage.setItem(LSKEY, JSON.stringify({ step: step, tab: tab, pos: winPos, fps: showFps })); } catch (e) {} }
  function loadState() { try { var s = JSON.parse(localStorage.getItem(LSKEY) || "{}"); if ([1, 10, 100].indexOf(s.step) >= 0) step = s.step; if (["vals", "game", "scan", "act", "saves"].indexOf(s.tab) >= 0) tab = s.tab; if (s.pos) winPos = s.pos; if (s.fps) setFps(true); } catch (e) {} }
  function hasGameTab() { return true; }   // там же профиль игры — нужен любому движку
  var jumpList = null, jumpFilter = "";

  // --- скорость игры: виртуальное время. Движки HTML5 считают кадр по performance.now
  // или по метке requestAnimationFrame — подменяем обе (и Date.now), темп = k.
  var speed = 1, TIME = null;
  function timeSpeed(k) {
    if (!TIME) {
      var pn = performance.now.bind(performance), dn = Date.now, raf = window.requestAnimationFrame;
      TIME = { k: 1, pn: pn, rBase: pn(), vBase: pn() };
      var virt = function () { return TIME.vBase + (pn() - TIME.rBase) * TIME.k; };
      TIME.virt = virt;
      try { performance.now = virt; } catch (e) {}
      Date.now = function () { return dn() + Math.round(virt() - pn()); };
      if (raf) window.requestAnimationFrame = function (cb) { return raf.call(window, function () { cb(virt()); }); };
    }
    // смена темпа без скачка: виртуальное время продолжается с того же места
    TIME.vBase = TIME.virt(); TIME.rBase = TIME.pn(); TIME.k = k;
  }
  function setSpeed(k) {
    try { if (typeof A.speed === "function") A.speed(k); else timeSpeed(k); speed = k; }
    catch (e) { console.error(T("[TM] скорость"), e); toast(T("Скорость не меняется"), true); return; }
    var b = document.getElementById("tm-speed");
    if (k === 1) { if (b) b.remove(); return; }
    if (!b) { b = el("div"); b.id = "tm-speed"; document.body.appendChild(b); }
    b.textContent = k === 0 ? T("ПАУЗА") : "×" + k;
  }
  // шаг кадра на паузе: виртуальное время сдвигается ровно на один кадр (1/60 с);
  // у движков со своей скоростью (RPG Maker) — их step()
  function frameStep() {
    if (speed !== 0) setSpeed(0);
    try {
      if (typeof A.speed === "function") { if (A.step) A.step(); else throw new Error(T("нет step")); }
      else if (TIME) TIME.vBase += 1000 / 60;
    } catch (e) { console.error(T("[TM] шаг кадра"), e); toast(T("Шаг кадра здесь не работает"), true); }
  }

  // счётчик FPS: реальные кадры браузера за последнюю секунду (своим циклом requestAnimationFrame)
  var showFps = false, fpsVal = 0, fpsN = 0, fpsT = 0, fpsLoop = false;
  var realNow = performance.now.bind(performance), realRaf = window.requestAnimationFrame;
  function fpsTick() {
    if (!showFps) { fpsLoop = false; return; }
    fpsN++;
    var t = realNow();
    if (t - fpsT >= 500) {
      fpsVal = Math.round(fpsN * 1000 / (t - fpsT)); fpsN = 0; fpsT = t;
      var b = document.getElementById("tm-fps");
      if (!b && document.body) { b = el("div"); b.id = "tm-fps"; document.body.appendChild(b); }
      if (b) b.textContent = "FPS " + fpsVal;
    }
    realRaf.call(window, fpsTick);
  }
  function setFps(on) {
    showFps = on;
    if (!on) { var b = document.getElementById("tm-fps"); if (b) b.remove(); return; }
    if (!fpsLoop && realRaf) { fpsLoop = true; fpsN = 0; fpsT = realNow(); realRaf.call(window, fpsTick); }
  }

  try { if (JSON.parse(localStorage.getItem(LSKEY) || "{}").fps) setFps(true); } catch (e) {}

  // точки телепорта: localStorage, свои у каждого движка/игры
  var PKEY = LSKEY + "_places_" + (location.pathname || "");
  function loadPlaces() { try { return JSON.parse(localStorage.getItem(PKEY) || "[]"); } catch (e) { return []; } }
  function savePlaces(a) { try { localStorage.setItem(PKEY, JSON.stringify(a)); } catch (e) {} }

  // --- профиль игры: темп, включённые режимы и заморозки, которые ставятся сами при запуске
  var FKEY = LSKEY + "_profile_" + (location.pathname || "");
  function loadProfile() { try { return JSON.parse(localStorage.getItem(FKEY) || "null"); } catch (e) { return null; } }
  function profileNow() {
    var p = { speed: speed, cheats: {}, frozen: {} };
    (A.cheats ? A.cheats() || [] : []).forEach(function (c) { try { if (c.get()) p.cheats[c.label] = true; } catch (e) {} });
    Object.keys(frozen).forEach(function (k) { p.frozen[k] = frozen[k].v; });
    return p;
  }
  // строки «Значений» по ключу заморозки «раздел/имя»
  function rowsByKey() {
    var out = {};
    (A.stats() || []).forEach(function (sec) {
      (sec.rows || []).forEach(function (r) { out[(sec.title || "") + "/" + r.name] = r; });
    });
    return out;
  }
  function applyProfile(p) {
    if (p.speed != null && p.speed !== 1) setSpeed(p.speed);
    (A.cheats ? A.cheats() || [] : []).forEach(function (c) { if (p.cheats && p.cheats[c.label]) { try { c.set(true); } catch (e) {} } });
    var rows = Object.keys(p.frozen || {}).length ? rowsByKey() : {}, n = 0;
    Object.keys(p.frozen || {}).forEach(function (k) {
      var r = rows[k];
      if (!r) return;
      frozen[k] = { v: p.frozen[k], set: r.set, get: r.get };
      n++;
    });
    if (n) startTick();
    return n;
  }
  function notice(msg) {
    var b = el("div", null, msg);
    b.style.cssText = "position:fixed;left:50%;top:14px;transform:translateX(-50%);z-index:2147482999;background:" + ACCENT +
      ";color:" + K.on_accent + ";font:700 13px 'Segoe UI',sans-serif;padding:7px 16px;border-radius:10px;pointer-events:none";
    document.body.appendChild(b);
    setTimeout(function () { b.remove(); }, 3500);
  }
  // ждём, пока игра загрузит данные (до минуты), и ставим профиль один раз
  (function autoProfile() {
    var p = loadProfile(), tries = 0;
    if (!p) return;
    var t = setInterval(function () {
      var ok = false;
      try { ok = A.ready() && document.body; } catch (e) {}
      if (!ok && ++tries < 120) return;
      clearInterval(t);
      if (ok) { var n = applyProfile(p); notice(T("TEST MENU: профиль игры применён") + (n ? T(" (заморозок: ") + n + ")" : "")); }
    }, 500);
  })();

  // --- журнал изменений: раз в секунду сверяются значения «Значений»; изменение без
  // пометки — «игра», правка из меню и возврат заморозкой помечаются там, где делаются
  var changelog = [], jPrev = {}, jSrc = {}, J_MAX = 300, J_ROWS = 400;
  function jMark(key, who) { jSrc[key] = who; }
  function journalTick() {
    var rows;
    try { if (!A.ready()) return; rows = rowsByKey(); } catch (e) { return; }
    var keys = Object.keys(rows).slice(0, J_ROWS), now = new Date();
    keys.forEach(function (k) {
      var v;
      try { v = rows[k].get(); } catch (e) { return; }
      var t = typeof v;
      if (!(t === "number" || t === "string" || t === "boolean")) return;
      if (k in jPrev && jPrev[k] !== v) {
        changelog.push({ t: now, key: k, from: jPrev[k], to: v, who: jSrc[k] || T("игра") });
      }
      jPrev[k] = v;
    });
    jSrc = {};
    if (changelog.length > J_MAX) changelog.splice(0, changelog.length - J_MAX);
  }
  setInterval(journalTick, 1000);
  function hhmmss(d) { return d.toTimeString().slice(0, 8); }
  function journalLines() {
    return changelog.slice().reverse().map(function (c) {
      return hhmmss(c.t) + "  " + c.key + ": " + fmt(c.from) + " → " + fmt(c.to) + "  (" + c.who + ")";
    });
  }
  function showJournal() {
    var lines = journalLines();
    showInfo(T("Журнал изменений (") + changelog.length + ")",
      lines.length ? lines.slice(0, 200) : [T("Пока ничего не менялось. Журнал сверяет «Значения» раз в секунду.")],
      [[T("Скачать"), function () {
        var a = el("a");
        a.href = URL.createObjectURL(new Blob([journalLines().reverse().join("\n")], { type: "text/plain" }));
        a.download = "tm_journal.txt"; document.body.appendChild(a); a.click(); a.remove();
      }], [T("Очистить"), function () { changelog = []; showJournal(); }]]);
  }

  // --- пульт в студии (tmkit/bridge.py): раз в 0.7 с отдаём значения, забираем команды.
  // Включается во вкладке «Игра» и запоминается для этой игры; без студии — опрос раз в 3 с.
  var BKEY = LSKEY + "_bridge_" + (location.pathname || "");
  var BR = { on: false, ok: false, id: "web-" + Math.random().toString(36).slice(2, 10), timer: null };
  function bridgeState() {
    var rows = [], by = {};
    try { by = rowsByKey(); } catch (e) {}
    Object.keys(by).slice(0, 600).forEach(function (k) {
      var r = by[k], v;
      try { v = r.get(); } catch (e) { return; }
      var t = typeof v;
      if (!(t === "number" || t === "string" || t === "boolean")) return;
      var cut = k.indexOf("/");
      rows.push({ k: k, sec: k.slice(0, cut), name: r.name, type: r.type, v: v, fz: !!frozen[k] });
    });
    var caps = ["set", "freeze"];
    if (A.speed) caps.push("speed");
    if (A.speed === true || A.step) caps.push("step");
    return { id: BR.id, title: document.title || A.title, engine: A.title, caps: caps, speed: speed, rows: rows };
  }
  function bridgeApply(cmds) {
    var by = null;
    (cmds || []).forEach(function (c) {
      try {
        if (c.op === "speed") { setSpeed(Number(c.v)); return; }
        if (c.op === "step") { frameStep(); return; }
        by = by || rowsByKey();
        var r = by[c.k];
        if (!r) return;
        if (c.op === "set") {
          var v = r.type === "num" ? Number(c.v) : r.type === "bool" ? (c.v === true || c.v === "true" || c.v === 1) : String(c.v);
          jMark(c.k, T("пульт")); r.set(v);
          if (frozen[c.k]) frozen[c.k].v = r.get();
        } else if (c.op === "freeze") {
          frozen[c.k] = { v: r.get(), set: r.set, get: r.get }; startTick();
        } else if (c.op === "unfreeze") {
          delete frozen[c.k];
        }
      } catch (e) { console.error(T("[TM] пульт"), e); }
    });
    if (overlay && cmds && cmds.length) live.forEach(function (f) { try { f(); } catch (e) {} });
  }
  function bridgeTick() {
    BR.timer = null;
    if (!BR.on) return;
    var body;
    try { body = JSON.stringify(A.ready() ? bridgeState() : { id: BR.id, title: document.title, engine: A.title, rows: [] }); } catch (e) { body = "{}"; }
    fetch("http://127.0.0.1:47820/sync", { method: "POST", body: body, headers: { "Content-Type": "text/plain" } })
      .then(function (r) { return r.json(); })
      .then(function (d) { BR.ok = true; bridgeApply(d.cmds); BR.timer = setTimeout(bridgeTick, 700); })
      .catch(function () { BR.ok = false; BR.timer = setTimeout(bridgeTick, 3000); });
  }
  function setBridge(on) {
    BR.on = on;
    try { if (on) localStorage.setItem(BKEY, "1"); else localStorage.removeItem(BKEY); } catch (e) {}
    if (on && !BR.timer) bridgeTick();
  }
  try { if (localStorage.getItem(BKEY)) setBridge(true); } catch (e) {}

  // ------------------------------------------------------------------ стиль
  function injectCss() {
    if (document.getElementById("tm-style")) return;
    var s = document.createElement("style");
    s.id = "tm-style";
    s.textContent = [
      "@keyframes tmFade{from{opacity:0}to{opacity:1}}",
      "@keyframes tmPop{from{opacity:0;transform:translateY(8px) scale(.98)}to{opacity:1;transform:none}}",
      "#tm-ov{position:fixed;inset:0;z-index:2147483000;background:radial-gradient(1200px 820px at 50% 28%,rgba(8,12,20,.7),rgba(4,6,11,.84));",
      "backdrop-filter:blur(7px);-webkit-backdrop-filter:blur(7px);display:flex;align-items:center;",
      "justify-content:center;animation:tmFade .16s ease;font-family:'Segoe UI',system-ui,-apple-system,sans-serif}",
      "#tm-win{width:min(720px,94vw);max-height:84vh;display:flex;flex-direction:column;",
      "background:linear-gradient(180deg,rgba(22,27,38,.98),rgba(15,19,28,.98));border:1px solid " + ACCENT + "4d;border-radius:20px;overflow:hidden;",
      "color:" + K.text + ";box-shadow:0 32px 90px -20px rgba(0,0,0,.7),0 0 0 1px rgba(255,255,255,.04) inset,0 0 64px -24px " + ACCENT + "aa;",
      "animation:tmPop .2s cubic-bezier(.2,.7,.3,1)}",
      "#tm-head{background:linear-gradient(135deg," + ACCENT + "," + ACCENT + "d0);color:" + K.on_accent + ";",
      "padding:14px 16px;display:flex;gap:12px;align-items:center;cursor:move;user-select:none;",
      "box-shadow:inset 0 1px 0 rgba(255,255,255,.28)}",
      "#tm-head .dot{flex:none;margin-right:30px;width:9px;height:9px;border-radius:50%;background:" + K.on_accent + "66;box-shadow:15px 0 0 " + K.on_accent + "40,30px 0 0 " + K.on_accent + "26}",
      "#tm-head .t{flex:1;font-weight:800;font-size:16px;letter-spacing:.3px}",
      "#tm-head .t small{display:block;font-weight:600;font-size:11px;opacity:.68;letter-spacing:.2px}",
      "#tm-head button{background:" + K.on_accent + "26;color:" + K.on_accent + ";border:0;border-radius:9px;width:32px;height:29px;",
      "cursor:pointer;font-weight:800;font-size:14px;transition:background .12s}",
      "#tm-head button:hover{background:" + K.on_accent + "45}",
      "#tm-tabs{display:flex;gap:5px;padding:7px;background:#0d111a;border-bottom:1px solid #ffffff0d}",
      "#tm-tabs button{flex:1;background:transparent;color:" + K.text_hint + ";border:0;border-radius:11px;padding:9px 8px;cursor:pointer;",
      "font-size:13px;font-weight:700;transition:all .14s}",
      "#tm-tabs button:hover{color:" + K.text + ";background:#ffffff0a}",
      "#tm-tabs button.on{color:" + K.on_accent + ";background:linear-gradient(180deg," + ACCENT + "," + ACCENT + "cc)}",
      "#tm-tools{display:flex;gap:8px;align-items:center;padding:9px 16px;background:" + K.bg_window + ";",
      "font-size:12px;color:" + K.text_hint + ";flex-wrap:wrap;border-bottom:1px solid #ffffff08}",
      "#tm-tools .seg{display:inline-flex;background:#ffffff0d;border-radius:10px;padding:3px;gap:2px}",
      "#tm-tools .seg button{background:transparent;color:" + K.text_dim + ";border:0;border-radius:8px;padding:4px 12px;",
      "cursor:pointer;font-size:12px;font-weight:700;transition:all .12s}",
      "#tm-tools .seg button.on{background:linear-gradient(180deg," + ACCENT + "," + ACCENT + "cc);color:" + K.on_accent + "}",
      "#tm-body{overflow:auto;padding:8px 12px 12px;scrollbar-width:thin;scrollbar-color:" + K.line + " transparent}",
      "#tm-win button:focus-visible,.tm-finput:focus-visible{outline:2px solid " + ACCENT + ";outline-offset:2px}",
      "#tm-head button:focus-visible{outline-color:" + K.on_accent + "}",
      "@media(prefers-reduced-motion:reduce){#tm-ov,#tm-win{animation:none}#tm-win *,.tm-row,.tm-act,.tm-row .ctrl button{transition:none!important}.tm-act:hover,.tm-row .ctrl button:hover{transform:none}}",
      ".tm-filter{padding:2px 2px 10px;position:sticky;top:-10px;background:rgba(20,25,35,.98);z-index:1}",
      ".tm-filter{display:flex;gap:8px}.tm-jbtn{flex:none;background:#ffffff0d;color:" + K.text_dim + ";border:1px solid " + K.line + ";border-radius:10px;padding:0 12px;cursor:pointer;font-size:12.5px;font-weight:700}",
      ".tm-finput{width:100%;box-sizing:border-box;background:" + K.bg_window + ";border:1px solid " + K.line + ";border-radius:10px;",
      "color:" + K.text + ";padding:9px 12px;font-size:13px;outline:none;transition:border-color .12s,box-shadow .12s}",
      ".tm-finput:focus{border-color:" + ACCENT + ";box-shadow:0 0 0 3px " + ACCENT + "22}",
      ".tm-sec{color:" + ACCENT + ";font-size:11px;font-weight:800;text-transform:uppercase;letter-spacing:1px;",
      "margin:16px 6px 8px;display:flex;align-items:center;gap:10px}",
      ".tm-sec::after{content:'';flex:1;height:1px;background:linear-gradient(90deg," + ACCENT + "40,transparent)}",
      ".tm-row{display:flex;gap:10px;align-items:center;padding:9px 11px;border-radius:11px;transition:background .12s,box-shadow .12s}",
      ".tm-row:hover{background:#ffffff0a;box-shadow:inset 2px 0 0 " + ACCENT + "}",
      ".tm-row .k{flex:1;font-size:13.5px;word-break:break-word}",
      ".tm-row .v{font-family:'Consolas','SF Mono',monospace;font-size:13px;font-weight:800;color:" + ACCENT + ";",
      "background:" + ACCENT + "1c;border:1px solid " + ACCENT + "33;padding:3px 10px;border-radius:8px;min-width:58px;text-align:right}",
      ".tm-row .ctrl{display:flex;gap:5px}",
      ".tm-row .ctrl button{background:linear-gradient(180deg,#232a38,#191f2c);color:" + K.text + ";border:1px solid " + K.line + ";border-radius:9px;min-width:32px;height:32px;",
      "padding:0 9px;cursor:pointer;font-size:14px;font-weight:700;transition:all .1s}",
      ".tm-ico{width:18px;height:18px;vertical-align:middle;pointer-events:none}",
      ".tm-row .ctrl button.on{background:" + ACCENT + ";color:" + K.on_accent + ";border-color:" + ACCENT + "}",
      ".tm-row .ctrl button:hover{background:linear-gradient(180deg," + ACCENT + "," + ACCENT + "cc);color:" + K.on_accent + ";border-color:" + ACCENT + ";transform:translateY(-1px)}",
      ".tm-msg{color:" + K.text_dim + ";font-size:13px;padding:8px 6px;line-height:1.4}",
      ".tm-msg b{color:" + ACCENT + "}",
      ".tm-scanbar{display:flex;flex-wrap:wrap;gap:6px;padding:6px 4px}",
      ".tm-scanbar button{background:linear-gradient(180deg,#232a38,#191f2c);color:" + K.text + ";border:1px solid " + K.line + ";border-radius:9px;padding:8px 13px;cursor:pointer;font-size:12.5px;font-weight:600;transition:all .1s}",
      ".tm-scanbar button:hover{background:linear-gradient(180deg," + ACCENT + "," + ACCENT + "cc);color:" + K.on_accent + ";border-color:" + ACCENT + "}",
      ".tm-up{color:" + K.ok + "}.tm-down{color:" + K.err + "}",
      ".tm-act{padding:13px 15px;margin:7px 4px;border-radius:13px;background:linear-gradient(180deg,#ffffff0d,#ffffff05);border:1px solid #ffffff12;border-left:3px solid " + ACCENT + "80;",
      "cursor:pointer;transition:all .14s}",
      ".tm-act:hover{background:" + ACCENT + "1f;border-color:" + ACCENT + "80;border-left-color:" + ACCENT + ";transform:translateY(-2px);box-shadow:0 12px 26px -12px " + ACCENT + "aa}",
      ".tm-act .l{font-size:14px;font-weight:700}",
      ".tm-act .d{font-size:11.5px;color:" + K.text_hint + ";margin-top:4px;font-family:'Consolas',monospace}",
      "#tm-foot{padding:10px 16px;background:" + K.bg_deep + ";color:" + K.text_off + ";font-size:11.5px;border-top:1px solid #ffffff0a}",
      "#tm-foot kbd{background:" + K.bg_control + ";border:1px solid " + K.line + ";border-radius:6px;padding:1px 6px;font-size:11px;color:" + K.text_dim + "}",
      "#tm-toast{position:absolute;left:50%;bottom:60px;transform:translateX(-50%);background:linear-gradient(180deg," + ACCENT + "," + ACCENT + "cc);",
      "color:" + K.on_accent + ";font-weight:800;font-size:13px;padding:9px 20px;border-radius:12px;opacity:0;",
      "transition:opacity .2s;pointer-events:none;box-shadow:0 10px 30px -8px " + ACCENT + "aa}",
      "#tm-toast.err{background:" + K.err + ";color:#160404}",
      "#tm-fps{position:fixed;left:12px;top:10px;z-index:2147482999;background:" + K.bg_window + "e6;color:" + ACCENT + ";font:800 13px 'Consolas',monospace;",
      "padding:4px 10px;border-radius:9px;border:1px solid " + ACCENT + "55;pointer-events:none}",
      "#tm-speed{position:fixed;right:12px;top:10px;z-index:2147482999;background:" + ACCENT + ";color:" + K.on_accent + ";font:800 13px 'Segoe UI',sans-serif;",
      "padding:4px 10px;border-radius:9px;pointer-events:none;box-shadow:0 6px 18px -6px #000a}",
      "#tm-body::-webkit-scrollbar{width:11px}#tm-body::-webkit-scrollbar-thumb{background:" + K.line + ";border-radius:6px;border:3px solid transparent;background-clip:padding-box}",
      "#tm-body::-webkit-scrollbar-thumb:hover{background:" + ACCENT + ";background-clip:padding-box}"
    ].join("");
    document.head.appendChild(s);
  }

  // ------------------------------------------------------------------ helpers
  function el(tag, cls, txt) { var e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
  function mkBtn(parent, label, fn) { var b = el("button", null, label); b.addEventListener("click", fn); parent.appendChild(b); return b; }
  // кнопка-значок из TM_ICONS (tm_icons.js, data-URI); без значков — текстовая подпись
  function mkIco(parent, ico, alt, fn, tip, text) {
    var src = (typeof TM_ICONS !== "undefined" && TM_ICONS) ? TM_ICONS[ico] : null;
    var b = mkBtn(parent, src ? null : (text ? (alt ? alt + " " : "") + text : alt), fn);
    if (src) {
      var im = el("img", "tm-ico"); im.src = src; im.alt = alt; b.appendChild(im);
      if (text) b.appendChild(document.createTextNode(" " + text));
    }
    if (tip) b.title = tip;
    return b;
  }
  function fmt(v, type) {
    if (type === "bool") return v ? T("ВКЛ") : T("выкл");
    // дробные (координаты, таймеры) — не длиннее 3 знаков после точки
    if (typeof v === "number" && v % 1 !== 0) return String(Math.round(v * 1000) / 1000);
    return String(v);
  }

  function section(list, title) { list.appendChild(el("div", "tm-sec", title)); }
  function row(list, name, valStr) {
    var r = el("div", "tm-row");
    r.appendChild(el("div", "k", name));
    var v = el("div", "v", valStr); r.appendChild(v);
    var ctrl = el("div", "ctrl"); r.appendChild(ctrl);
    list.appendChild(r);
    return { row: r, ctrl: ctrl, setV: function (s) { v.textContent = s; } };
  }

  var toastTimer = null;
  function toast(msg, isErr) {
    if (!overlay) return;
    var t = overlay.querySelector("#tm-toast");
    if (!t) { t = el("div", null, ""); t.id = "tm-toast"; overlay.appendChild(t); }
    t.className = isErr ? "err" : "";
    t.textContent = msg; t.style.opacity = "1";
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { t.style.opacity = "0"; }, 1100);
  }

  // ------------------------------------------------------------------ вкладки
  function applyFilter(list) {
    var q = filter;
    Array.prototype.forEach.call(list.querySelectorAll(".tm-row"), function (r) {
      var k = r.querySelector(".k");
      if (!k) return;
      r.style.display = (!q || k.textContent.toLowerCase().indexOf(q) >= 0) ? "" : "none";
    });
  }

  function renderVals(list) {
    var secs = A.stats() || [];
    if (!secs.length) { list.appendChild(el("div", "tm-msg", A.footMissing || T("Данные недоступны."))); return; }

    var fbar = el("div", "tm-filter");
    var inp = el("input", "tm-finput");
    inp.type = "text"; inp.placeholder = T("фильтр по имени…"); inp.value = filter;
    inp.addEventListener("input", function () { filter = inp.value.toLowerCase(); applyFilter(list); });
    fbar.appendChild(inp);
    var jb = mkBtn(fbar, T("журнал: ") + changelog.length, showJournal);
    jb.className = "tm-jbtn"; jb.title = T("Что, когда и кем изменено: игрой, меню или заморозкой");
    list.appendChild(fbar);

    secs.forEach(function (sec) {
      if (sec.title) section(list, sec.title);
      (sec.rows || []).forEach(function (r) {
        var h = row(list, r.name, fmt(r.get(), r.type));
        var fkey = (sec.title || "") + "/" + r.name;
        function rf() { h.setV(fmt(r.get(), r.type)); }
        // правка замороженного значения = новое удерживаемое значение
        function put(v) { jMark(fkey, T("меню")); r.set(v); if (frozen[fkey]) frozen[fkey].v = r.get(); rf(); }
        live.push(rf);
        if (r.where) mkBtn(h.ctrl, T("где"), function () {
          toast(A.whereHint || T("Ищу в событиях игры…"));
          r.where(function (lines) { whereDone(r.name, lines); });
        }).title = A.whereTip || T("Где игра меняет и проверяет это значение");
        if (r.type === "num") {
          mkBtn(h.ctrl, "−", function () { put(r.get() - step); });
          mkBtn(h.ctrl, "+", function () { put(r.get() + step); });
          mkIco(h.ctrl, "edit", T("ввод"), function () { var v = prompt(r.name + ":", String(r.get())); if (v !== null && v.trim() !== "" && !isNaN(Number(v))) put(Number(v)); }, T("Ввести значение"));
          var fb = mkIco(h.ctrl, "snow", T("стоп"), function () {
            if (frozen[fkey]) delete frozen[fkey]; else frozen[fkey] = { v: r.get(), set: r.set, get: r.get };
            fb.className = frozen[fkey] ? "on" : "";
          });
          fb.title = T("Заморозить: игра не сможет изменить значение");
          if (frozen[fkey]) { frozen[fkey].set = r.set; frozen[fkey].get = r.get; fb.className = "on"; }
        } else if (r.type === "bool") {
          mkIco(h.ctrl, "swap", T("вкл/выкл"), function () { jMark(fkey, T("меню")); r.set(!r.get()); rf(); }, T("Переключить"));
        } else {
          mkIco(h.ctrl, "edit", T("ввод"), function () { var v = prompt(r.name + ":", String(r.get())); if (v !== null) { jMark(fkey, T("меню")); r.set(v); rf(); } }, T("Ввести значение"));
        }
      });
    });
    applyFilter(list);
  }

  // ответ «где»: меню открыто — сразу, закрыто — по следующему открытию (и уведомление)
  var pendingInfo = null;
  function whereDone(title, lines) {
    if (bodyEl) { showInfo(title, lines); return; }
    pendingInfo = [title, lines];
    notice("TEST MENU: «" + title + T("» — готово, открой меню (Shift+T)"));
  }

  // окно-справка поверх вкладки: «← назад» возвращает список
  function showInfo(title, lines, extra) {
    if (!bodyEl) return;
    live = [];
    bodyEl.innerHTML = "";
    var bar = el("div", "tm-scanbar");
    mkBtn(bar, T("← назад"), rerender);
    (extra || []).forEach(function (b) { mkBtn(bar, b[0], b[1]); });
    bodyEl.appendChild(bar);
    section(bodyEl, title);
    lines.forEach(function (l) { bodyEl.appendChild(el("div", "tm-msg", l)); });
  }

  function scanNarrow(mode) {
    if (!scanCands) { scanMsg = T("Сначала «Снимок»."); return; }
    var cur = A.nums(), keep = [];
    scanCands.forEach(function (k) {
      var a = scanSnap[k], b = cur[k];
      if (a == null || b == null) return;
      var ok = mode === "changed" ? b !== a : mode === "same" ? b === a : mode === "up" ? b > a : mode === "down" ? b < a : false;
      if (ok) keep.push(k);
    });
    scanCands = keep; scanSnap = cur; scanMsg = T("Осталось кандидатов: <b>") + keep.length + "</b>";
  }
  function renderScan(list) {
    var bar = el("div", "tm-scanbar");
    mkIco(bar, "camera", "", function () { scanSnap = A.nums(); scanCands = Object.keys(scanSnap); scanMsg = T("Снимок: <b>") + scanCands.length + T("</b> числовых. Измени в игре и сужай."); rerender(); }, T("Запомнить текущие числа"), T("Снимок"));
    mkBtn(bar, T("изменились"), function () { scanNarrow("changed"); rerender(); });
    mkBtn(bar, T("не изменились"), function () { scanNarrow("same"); rerender(); });
    mkBtn(bar, T("больше ▲"), function () { scanNarrow("up"); rerender(); });
    mkBtn(bar, T("меньше ▼"), function () { scanNarrow("down"); rerender(); });
    mkBtn(bar, T("сброс"), function () { scanSnap = {}; scanCands = null; scanMsg = T("Сброшено."); rerender(); });
    list.appendChild(bar);
    var m = el("div", "tm-msg"); m.innerHTML = scanMsg; list.appendChild(m);
    if (scanCands && scanCands.length && scanCands.length <= 60) {
      var cur = A.nums();
      scanCands.slice().sort().forEach(function (k) {
        var o = scanSnap[k], c = cur[k];
        var h = row(list, k, "");
        var vv = h.row.querySelector(".v");
        vv.textContent = o + " → " + c;
        if (c > o) vv.className = "v tm-up"; else if (c < o) vv.className = "v tm-down";
      });
    } else if (scanCands && scanCands.length > 60) {
      list.appendChild(el("div", "tm-msg", T("Слишком много (") + scanCands.length + T(") — сужай кнопками выше.")));
    }
  }

  function renderActions(list) {
    (A.actions() || []).forEach(function (a) {
      var card = el("div", "tm-act");
      card.appendChild(el("div", "l", a.label));
      if (a.desc) card.appendChild(el("div", "d", a.desc));
      card.addEventListener("click", function () {
        try { a.run(); toast(T("Готово")); if (tab !== "act") rerender(); }
        catch (e) { toast(T("Ошибка"), true); console.error("[TM]", e); }
      });
      list.appendChild(card);
    });
  }

  function renderGame(list) {
    if (A.speed) {
      section(list, T("Скорость игры"));
      var bar = el("div", "tm-scanbar");
      [[0, T("пауза")], [0.25, "×0.25"], [0.5, "×0.5"], [1, "×1"], [2, "×2"], [3, "×3"], [5, "×5"]].forEach(function (d) {
        var b = mkBtn(bar, d[1], function () { setSpeed(d[0]); rerender(); });
        if (d[0] === speed) { b.style.background = ACCENT; b.style.color = K.on_accent; }
      });
      list.appendChild(bar);
      list.appendChild(el("div", "tm-msg", T("Ускорение — пропускать бои и прогулки, замедление и пауза — разглядеть и успеть. Значок в углу показывает темп, пока он не ×1.")));
      var sb = el("div", "tm-scanbar");
      mkBtn(sb, T("Шаг кадра"), function () { frameStep(); rerender(); }).title = T("Игра на паузе продвигается ровно на один кадр — разглядеть анимацию или баг");
      var fb = mkBtn(sb, showFps ? T("FPS в углу: вкл") : T("FPS в углу: выкл"), function () { setFps(!showFps); saveState(); rerender(); });
      if (showFps) { fb.style.background = ACCENT; fb.style.color = K.on_accent; }
      list.appendChild(sb);
    }
    var ch = A.cheats ? (A.cheats() || []) : [];
    if (ch.length) {
      section(list, T("Режимы"));
      ch.forEach(function (c) {
        var h = row(list, c.label, fmt(c.get(), "bool"));
        if (c.desc) h.row.title = c.desc;
        function rf() { h.setV(fmt(c.get(), "bool")); }
        live.push(rf);
        mkIco(h.ctrl, "swap", T("вкл/выкл"), function () { try { c.set(!c.get()); } catch (e) { toast(T("Ошибка"), true); console.error("[TM]", e); } rf(); }, c.desc || T("Переключить"));
      });
    }
    if (A.jumps) {
      section(list, A.jumps.title || T("Переходы"));
      if (!jumpList) {
        var jb = el("div", "tm-scanbar");
        mkBtn(jb, T("Показать список"), function () {
          toast(T("Загружаю…"));
          A.jumps.load(function (rows) { jumpList = rows; if (tab === "game") rerender(); });
        });
        list.appendChild(jb);
      } else {
        var jf = el("input", "tm-finput");
        jf.placeholder = T("фильтр…"); jf.value = jumpFilter;
        jf.addEventListener("input", function () {
          jumpFilter = jf.value.toLowerCase();
          Array.prototype.forEach.call(list.querySelectorAll(".tm-jump"), function (r) {
            r.style.display = r.textContent.toLowerCase().indexOf(jumpFilter) >= 0 ? "" : "none";
          });
        });
        list.appendChild(jf);
        jumpList.forEach(function (j) {
          var h = row(list, j.name, "");
          h.row.classList.add("tm-jump");
          h.row.querySelector(".v").remove();
          if (j.hint) h.row.title = j.hint;
          mkBtn(h.ctrl, T("перейти"), function () { try { j.go(); close(); } catch (e) { toast(T("Не вышло"), true); console.error("[TM]", e); } });
          if (jumpFilter && j.name.toLowerCase().indexOf(jumpFilter) < 0) h.row.style.display = "none";
        });
      }
    }
    section(list, T("Пульт в студии"));
    var bb = el("div", "tm-scanbar");
    var bbtn = mkBtn(bb, BR.on ? T("Пульт: вкл") : T("Пульт: выкл"), function () { setBridge(!BR.on); rerender(); });
    if (BR.on) { bbtn.style.background = ACCENT; bbtn.style.color = K.on_accent; }
    bbtn.title = T("Значения, заморозки, темп и шаг кадра — из окна «Пульт» студии (второй монитор)");
    list.appendChild(bb);
    list.appendChild(el("div", "tm-msg", BR.on ? (BR.ok ? T("Связь со студией есть.") : T("Жду студию: открой в ней «Пульт»."))
      : T("Включи, чтобы управлять игрой из студии, не открывая меню поверх игры.")));
    section(list, T("Язык меню"));
    var lb = el("div", "tm-scanbar");
    [["ru", "Русский"], ["en", "English"]].forEach(function (d) {
      var b = mkBtn(lb, d[1], function () { tmSetLang(d[0]); close(); open(); tab = "game"; rerender(); });
      if (TM_LANG === d[0]) { b.style.background = ACCENT; b.style.color = K.on_accent; }
    });
    list.appendChild(lb);
    section(list, T("Профиль игры"));
    var pr = loadProfile(), prb = el("div", "tm-scanbar");
    mkBtn(prb, T("Сохранить профиль"), function () {
      try { localStorage.setItem(FKEY, JSON.stringify(profileNow())); toast(T("Профиль сохранён")); } catch (e) { toast(T("Не сохранить"), true); }
      rerender();
    }).title = T("Темп, включённые режимы и заморозки будут ставиться сами при каждом запуске игры");
    if (pr) mkBtn(prb, T("Удалить профиль"), function () { try { localStorage.removeItem(FKEY); } catch (e) {} rerender(); });
    list.appendChild(prb);
    list.appendChild(el("div", "tm-msg", pr
      ? T("Сейчас в профиле: темп ×") + pr.speed + T(", режимов ") + Object.keys(pr.cheats || {}).length + T(", заморозок ") + Object.keys(pr.frozen || {}).length + T(". Ставится сам при запуске игры.")
      : T("Профиля нет. Включи нужное (темп, режимы, заморозки во «Значениях») и нажми «Сохранить профиль».")));
    if (A.places) {
      section(list, T("Точки телепорта"));
      var pb = el("div", "tm-scanbar");
      mkBtn(pb, T("Запомнить место"), function () {
        var p = null;
        try { p = A.places.here(); } catch (e) { console.error("[TM]", e); }
        if (!p) { toast(T("Место сейчас не определить"), true); return; }
        var a = loadPlaces(); a.push(p); savePlaces(a); rerender();
      });
      list.appendChild(pb);
      var pl = loadPlaces();
      if (!pl.length) list.appendChild(el("div", "tm-msg", T("Пусто. Встань в нужное место и нажми «Запомнить место» — потом сюда можно вернуться одной кнопкой.")));
      pl.forEach(function (p, i) {
        var h = row(list, p.name || (T("точка ") + (i + 1)), "");
        h.row.querySelector(".v").remove();
        mkBtn(h.ctrl, T("сюда"), function () {
          try { A.places.go(p); close(); } catch (e) { toast(T("Не вышло"), true); console.error("[TM]", e); }
        });
        mkBtn(h.ctrl, "×", function () { var a = loadPlaces(); a.splice(i, 1); savePlaces(a); rerender(); }).title = T("Удалить точку");
      });
    }
  }

  // ------------------------------------------------------------------ вкладка «Сейвы»
  // Сохранения HTML5-игр почти всегда в localStorage (RPG Maker в браузере, SugarCube,
  // свои движки) или в IndexedDB (localforage, Construct, GDevelop). Здесь их видно и можно
  // править: JSON и сжатое LZString разворачиваются в список полей. Перед первой записью
  // ключа localStorage копия оригинала кладётся рядом (tm_bak:<ключ>) — «Вернуть оригинал».
  var BAK = "tm_bak:";
  var saveSel = null, saveDoc = null, saveFilter = "", idbInfo = null;

  function isOurKey(k) { return k.indexOf("tm_menu_") === 0 || k.indexOf(BAK) === 0; }
  function kb(n) { return n < 1024 ? n + T(" Б") : n < 1048576 ? (n / 1024).toFixed(1) + T(" КБ") : (n / 1048576).toFixed(1) + T(" МБ"); }

  // текст -> {kind, data}: json | lz64 (RPG Maker MV) | lz16 (SugarCube) | text
  function decodeText(raw) {
    try { return { kind: "json", data: JSON.parse(raw) }; } catch (e) {}
    var LZ = window.LZString;
    if (LZ) {
      var tries = [["lz64", "decompressFromBase64"], ["lz16", "decompressFromUTF16"]];
      for (var i = 0; i < tries.length; i++) {
        try {
          var t = LZ[tries[i][1]](raw);
          if (t && /^\s*[\[{]/.test(t)) return { kind: tries[i][0], data: JSON.parse(t) };
        } catch (e) {}
      }
    }
    return { kind: "text", data: raw };
  }
  function encodeText(kind, data) {
    if (kind === "text") return String(data);
    var s = JSON.stringify(data);
    if (kind === "lz64") return window.LZString.compressToBase64(s);
    if (kind === "lz16") return window.LZString.compressToUTF16(s);
    return s;
  }
  var KIND = { json: "JSON", lz64: "LZString (base64)", lz16: "LZString (UTF-16)", text: T("текст"), obj: T("объект") };

  // скалярные поля дерева: [{path:[…], name, v}]
  function flatten(obj) {
    var out = [], seen = [];
    (function walk(o, path, depth) {
      if (out.length > 3000) return;
      var t = typeof o;
      if (o === null || t === "number" || t === "string" || t === "boolean") {
        if (path.length) out.push({ path: path, name: path.join("."), v: o });
        return;
      }
      if (t !== "object" || depth > 7 || seen.indexOf(o) >= 0) return;
      seen.push(o);
      Object.keys(o).forEach(function (k) { walk(o[k], path.concat([k]), depth + 1); });
    })(obj, [], 0);
    return out;
  }
  function setPath(obj, path, v) {
    var o = obj;
    for (var i = 0; i < path.length - 1; i++) o = o[path[i]];
    o[path[path.length - 1]] = v;
  }

  function download(name, text) {
    var a = el("a");
    a.href = URL.createObjectURL(new Blob([text], { type: "application/json" }));
    a.download = name.replace(/[^\w.\- ]+/g, "_") + ".json";
    document.body.appendChild(a); a.click(); a.remove();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
  }

  // ---- IndexedDB (все вызовы асинхронные: по готовности — перерисовка вкладки)
  function idbOpen(name, cb, fail) {
    try {
      var rq = indexedDB.open(name);
      rq.onsuccess = function () { cb(rq.result); };
      rq.onerror = function () { fail(rq.error); };
      rq.onupgradeneeded = function () { try { rq.transaction.abort(); } catch (e) {} };  // базы нет — не создаём
    } catch (e) { fail(e); }
  }
  function idbScan(done) {
    var names = indexedDB.databases ? indexedDB.databases().then(function (l) { return l.map(function (d) { return d.name; }); })
      : Promise.resolve(["localforage"]);
    names.then(function (list) {
      var dbs = [], left = list.length;
      if (!left) return done(dbs);
      list.forEach(function (name) {
        idbOpen(name, function (db) {
          var stores = Array.prototype.slice.call(db.objectStoreNames), info = { name: name, stores: [] }, n = stores.length;
          dbs.push(info);
          if (!n) { db.close(); if (!--left) done(dbs); return; }
          stores.forEach(function (st) {
            var rq = db.transaction(st, "readonly").objectStore(st).getAllKeys(null, 500);
            rq.onsuccess = function () { info.stores.push({ name: st, keys: rq.result }); if (!--n) { db.close(); if (!--left) done(dbs); } };
            rq.onerror = function () { if (!--n) { db.close(); if (!--left) done(dbs); } };
          });
        }, function () { if (!--left) done(dbs); });
      });
    }, function () { done([]); });
  }
  function idbGet(sel, cb, fail) {
    idbOpen(sel.db, function (db) {
      var rq = db.transaction(sel.store, "readonly").objectStore(sel.store).get(sel.key);
      rq.onsuccess = function () { db.close(); cb(rq.result); };
      rq.onerror = function () { db.close(); fail(rq.error); };
    }, fail);
  }
  function idbPut(sel, value, cb, fail) {
    idbOpen(sel.db, function (db) {
      var os = db.transaction(sel.store, "readwrite").objectStore(sel.store);
      var rq = os.keyPath != null ? os.put(value) : os.put(value, sel.key);
      rq.onsuccess = function () { db.close(); cb(); };
      rq.onerror = function () { db.close(); fail(rq.error); };
    }, fail);
  }

  // открыть сейв: localStorage — сразу, IndexedDB — асинхронно
  function openSave(sel) {
    saveSel = sel; saveDoc = null; saveFilter = "";
    if (sel.kind === "ls") {
      var raw = localStorage.getItem(sel.key) || "", d = decodeText(raw);
      saveDoc = { kind: d.kind, data: d.data, raw: raw, dirty: false };
      rerender();
      return;
    }
    idbGet(sel, function (v) {
      var d = typeof v === "string" ? decodeText(v) : { kind: "obj", data: v };
      saveDoc = { kind: d.kind, data: d.data, raw: v, dirty: false, str: typeof v === "string" };
      if (tab === "saves") rerender();
    }, function (e) { toast(T("Не прочитать запись"), true); console.error("[TM]", e); });
  }

  function writeSave() {
    var sel = saveSel, doc = saveDoc;
    if (sel.kind === "ls") {
      try {
        if (localStorage.getItem(BAK + sel.key) == null && doc.raw.length < 1500000) localStorage.setItem(BAK + sel.key, doc.raw);
      } catch (e) {}
      try { localStorage.setItem(sel.key, encodeText(doc.kind, doc.data)); }
      catch (e) { toast(T("Не записать (место в хранилище?)"), true); console.error("[TM]", e); return; }
      doc.raw = localStorage.getItem(sel.key); doc.dirty = false;
      toast(T("Записано — загрузи этот сейв в игре")); rerender();
      return;
    }
    var val = doc.str ? encodeText(doc.kind, doc.data) : doc.data;
    idbPut(sel, val, function () { doc.dirty = false; toast(T("Записано — загрузи этот сейв в игре")); if (tab === "saves") rerender(); },
      function (e) { toast(T("Не записать в IndexedDB"), true); console.error("[TM]", e); });
  }

  function renderSaveDoc(list) {
    var sel = saveSel, doc = saveDoc;
    var bar = el("div", "tm-scanbar"), wb = null;
    mkBtn(bar, T("← к списку"), function () {
      if (doc && doc.dirty && !confirm(T("Правки не записаны. Выйти без записи?"))) return;
      saveSel = saveDoc = null; rerender();
    });
    // правка поля не перерисовывает список (иначе прокрутка улетала наверх) — только кнопку
    function markDirty() { doc.dirty = true; wb.textContent = T("Записать правки"); wb.style.background = ACCENT; wb.style.color = K.on_accent; }
    if (doc) {
      wb = mkBtn(bar, T("Правок нет"), function () { if (doc.dirty) writeSave(); });
      if (doc.dirty) markDirty();
      mkBtn(bar, T("Скачать копию"), function () {
        download((sel.kind === "ls" ? sel.key : sel.db + "_" + sel.key), typeof doc.raw === "string" ? doc.raw : JSON.stringify(doc.raw));
      }).title = T("Файл с текущим содержимым — на всякий случай");
      if (sel.kind === "ls" && localStorage.getItem(BAK + sel.key) != null) {
        mkBtn(bar, T("Вернуть оригинал"), function () {
          if (!confirm(T("Вернуть сейв к состоянию до первой правки из меню?"))) return;
          localStorage.setItem(sel.key, localStorage.getItem(BAK + sel.key));
          localStorage.removeItem(BAK + sel.key);
          openSave(sel); toast(T("Оригинал возвращён"));
        });
      }
    }
    list.appendChild(bar);
    section(list, sel.kind === "ls" ? "localStorage: " + sel.key : "IndexedDB: " + sel.db + " / " + sel.store + " / " + sel.key);
    if (!doc) { list.appendChild(el("div", "tm-msg", T("Читаю…"))); return; }
    list.appendChild(el("div", "tm-msg", T("Формат: ") + KIND[doc.kind] + T(". Правки записываются кнопкой «Записать правки»; игра увидит их, когда загрузит этот сейв.")));
    if (doc.kind === "text") {
      var tb = el("div", "tm-scanbar");
      mkBtn(tb, T("Изменить текст…"), function () {
        var v = prompt(sel.key + ":", String(doc.data));
        if (v !== null) { doc.data = v; doc.dirty = true; rerender(); }
      });
      list.appendChild(tb);
      list.appendChild(el("div", "tm-msg", String(doc.data).slice(0, 600) + (String(doc.data).length > 600 ? "…" : "")));
      return;
    }
    var fields = flatten(doc.data);
    var fbar = el("div", "tm-filter"), inp = el("input", "tm-finput");
    inp.placeholder = T("фильтр по полю… (") + fields.length + ")"; inp.value = saveFilter;
    inp.addEventListener("input", function () {
      saveFilter = inp.value.toLowerCase();
      Array.prototype.forEach.call(list.querySelectorAll(".tm-row"), function (r) {
        r.style.display = r.querySelector(".k").textContent.toLowerCase().indexOf(saveFilter) >= 0 ? "" : "none";
      });
    });
    fbar.appendChild(inp); list.appendChild(fbar);
    fields.slice(0, 1500).forEach(function (f) {
      var shown = typeof f.v === "string" && f.v.length > 60 ? f.v.slice(0, 60) + "…" : String(f.v);
      var h = row(list, f.name, shown);
      if (saveFilter && f.name.toLowerCase().indexOf(saveFilter) < 0) h.row.style.display = "none";
      function put(v) {
        setPath(doc.data, f.path, v); f.v = v; markDirty();
        h.setV(typeof v === "string" && v.length > 60 ? v.slice(0, 60) + "…" : String(v));
      }
      if (typeof f.v === "boolean") mkIco(h.ctrl, "swap", T("вкл/выкл"), function () { put(!f.v); }, T("Переключить"));
      else mkIco(h.ctrl, "edit", T("ввод"), function () {
        var v = prompt(f.name + ":", String(f.v));
        if (v === null) return;
        if (typeof f.v === "number") { if (v.trim() === "" || isNaN(Number(v))) { toast(T("Нужно число"), true); return; } put(Number(v)); }
        else put(v);
      }, T("Ввести значение"));
    });
    if (fields.length > 1500) list.appendChild(el("div", "tm-msg", T("Показаны первые 1500 полей — сузь фильтром.")));
  }

  function renderSaves(list) {
    if (saveSel) { renderSaveDoc(list); return; }
    section(list, "localStorage");
    var keys = [];
    try { for (var i = 0; i < localStorage.length; i++) keys.push(localStorage.key(i)); } catch (e) {}
    keys = keys.filter(function (k) { return !isOurKey(k); }).sort();
    if (!keys.length) list.appendChild(el("div", "tm-msg", T("Пусто: игра не хранит сейвы в localStorage (у RPG Maker на ПК они в файлах — их правит редактор сохранений студии).")));
    keys.forEach(function (k) {
      var raw = localStorage.getItem(k) || "";
      var h = row(list, k, kb(raw.length * 2) + (localStorage.getItem(BAK + k) != null ? T(", есть копия") : ""));
      mkBtn(h.ctrl, T("открыть"), function () { openSave({ kind: "ls", key: k }); });
    });
    section(list, "IndexedDB");
    if (!window.indexedDB) { list.appendChild(el("div", "tm-msg", T("IndexedDB недоступна."))); return; }
    if (!idbInfo) {
      var b = el("div", "tm-scanbar");
      mkBtn(b, T("Показать базы"), function () { toast(T("Читаю базы…")); idbScan(function (dbs) { idbInfo = dbs; if (tab === "saves") rerender(); }); });
      list.appendChild(b);
      return;
    }
    if (!idbInfo.length) list.appendChild(el("div", "tm-msg", T("Баз нет.")));
    idbInfo.forEach(function (db) {
      db.stores.forEach(function (st) {
        list.appendChild(el("div", "tm-msg", db.name + " / " + st.name + T(": записей ") + st.keys.length));
        st.keys.slice(0, 200).forEach(function (key) {
          var h = row(list, "  " + String(key), "");
          h.row.querySelector(".v").remove();
          mkBtn(h.ctrl, T("открыть"), function () { openSave({ kind: "idb", db: db.name, store: st.name, key: key }); });
        });
      });
    });
    var rb = el("div", "tm-scanbar");
    mkBtn(rb, T("Перечитать базы"), function () { idbInfo = null; rerender(); });
    list.appendChild(rb);
  }

  // Раз в 400 мс: вернуть замороженные значения и обновить показанные. Заморозка
  // работает и при закрытом меню — таймер живёт, пока есть хоть одно замороженное.
  function tick() {
    var any = false;
    Object.keys(frozen).forEach(function (k) {
      any = true;
      try { if (A.ready() && frozen[k].get() !== frozen[k].v) { jMark(k, T("заморозка")); frozen[k].set(frozen[k].v); } } catch (e) {}
    });
    if (overlay && (tab === "vals" || tab === "game")) live.forEach(function (f) { try { f(); } catch (e) {} });
    if (!overlay && !any) { clearInterval(liveTimer); liveTimer = null; }
  }
  function startTick() { if (!liveTimer) liveTimer = setInterval(tick, 400); }

  function rerender() {
    if (!bodyEl) return;
    live = [];
    bodyEl.innerHTML = "";
    if (!A.ready()) { bodyEl.appendChild(el("div", "tm-msg", A.footMissing || T("Данные игры недоступны."))); return; }
    if (tab === "game" && !hasGameTab()) tab = "vals";
    if (tab === "vals") renderVals(bodyEl);
    else if (tab === "game") renderGame(bodyEl);
    else if (tab === "scan") renderScan(bodyEl);
    else if (tab === "saves") renderSaves(bodyEl);
    else renderActions(bodyEl);
  }

  // ------------------------------------------------------------------ drag
  // Не дать окну уехать за край (сохранённая позиция + сменившийся размер окна игры).
  function clampWin() {
    if (!winEl || winEl.style.position !== "fixed") return;
    var r = winEl.getBoundingClientRect();
    var l = Math.min(Math.max(r.left, 80 - r.width), window.innerWidth - 80);
    var t = Math.min(Math.max(r.top, 0), window.innerHeight - 48);
    winEl.style.left = l + "px"; winEl.style.top = t + "px";
  }

  function enableDrag(head) {
    head.addEventListener("pointerdown", function (e) {
      if (e.target.closest("button")) return;
      var rect = winEl.getBoundingClientRect();
      var dx = e.clientX - rect.left, dy = e.clientY - rect.top;
      winEl.style.position = "fixed"; winEl.style.margin = "0";
      winEl.style.left = rect.left + "px"; winEl.style.top = rect.top + "px";
      function move(ev) { if (!winEl) return; winEl.style.left = (ev.clientX - dx) + "px"; winEl.style.top = (ev.clientY - dy) + "px"; }
      // capture: оверлей глушит всплытие событий мыши (см. open), до document они не дойдут
      function up() {
        document.removeEventListener("pointermove", move, true); document.removeEventListener("pointerup", up, true);
        if (!winEl) return;
        clampWin();
        winPos = { left: winEl.style.left, top: winEl.style.top }; saveState();
      }
      document.addEventListener("pointermove", move, true); document.addEventListener("pointerup", up, true);
      e.preventDefault();
    });
  }

  // ------------------------------------------------------------------ окно
  function close() {
    if (!overlay) return;
    overlay.remove(); overlay = null; winEl = bodyEl = null;
    if (A.onClose) { try { A.onClose(); } catch (e) { console.error("[TM]", e); } }
  }

  // Мышь/тач по оверлею не должны доходить до игры: движки слушают document
  // (RPG Maker по клику сквозь меню отправлял героя в точку под курсором).
  var SWALLOW = ["mousedown", "mouseup", "mousemove", "click", "dblclick", "contextmenu", "wheel",
                 "touchstart", "touchmove", "touchend", "pointerdown", "pointerup", "pointermove"];
  function swallow(e) { e.stopPropagation(); }

  function open() {
    injectCss();
    loadState();
    overlay = el("div"); overlay.id = "tm-ov";
    overlay.addEventListener("click", function (e) { if (e.target === overlay) close(); });
    SWALLOW.forEach(function (n) { overlay.addEventListener(n, swallow); });
    winEl = el("div"); winEl.id = "tm-win";

    var head = el("div"); head.id = "tm-head";
    head.appendChild(el("span", "dot"));
    var t = el("div", "t"); t.innerHTML = "TEST MENU<small>" + T(A.title || "") + "</small>"; head.appendChild(t);
    mkBtn(head, "X", close).title = T("Закрыть");
    winEl.appendChild(head);
    enableDrag(head);

    var tabs = el("div"); tabs.id = "tm-tabs";
    [["vals", T("Значения")], ["game", T("Игра")], ["scan", T("Сканер")], ["saves", T("Сейвы")], ["act", T("Экшены")]].forEach(function (d) {
      if (d[0] === "game" && !hasGameTab()) return;
      var b = mkBtn(tabs, d[1], function () { tab = d[0]; Array.prototype.forEach.call(tabs.children, function (o) { o.className = ""; }); b.className = "on"; saveState(); rerender(); });
      if (d[0] === tab) b.className = "on";
    });
    winEl.appendChild(tabs);

    var tools = el("div"); tools.id = "tm-tools";
    tools.appendChild(el("span", null, T("шаг:")));
    var seg = el("div", "seg");
    [1, 10, 100].forEach(function (s) {
      var b = mkBtn(seg, "×" + s, function () { step = s; Array.prototype.forEach.call(seg.children, function (o) { o.className = ""; }); b.className = "on"; saveState(); });
      if (s === step) b.className = "on";
    });
    tools.appendChild(seg);
    winEl.appendChild(tools);

    bodyEl = el("div"); bodyEl.id = "tm-body"; winEl.appendChild(bodyEl);

    var foot = el("div"); foot.id = "tm-foot";
    foot.innerHTML = A.ready()
      ? T("<kbd>Shift</kbd>+<kbd>T</kbd> меню | <kbd>Esc</kbd> закрыть | тяни за шапку")
      : (A.footMissing || T("Данные игры недоступны."));
    winEl.appendChild(foot);

    overlay.appendChild(winEl);
    document.body.appendChild(overlay);
    if (winPos && winPos.left) { winEl.style.position = "fixed"; winEl.style.margin = "0"; winEl.style.left = winPos.left; winEl.style.top = winPos.top; clampWin(); }
    rerender();
    if (pendingInfo) { showInfo(pendingInfo[0], pendingInfo[1]); pendingInfo = null; }
    startTick();
  }

  function toggle() { if (overlay) close(); else open(); }
  function isTyping(e) {
    var t = e.target;
    return !!t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.tagName === "SELECT" || t.isContentEditable);
  }
  // Один перехватчик на window (capture): хоткей меню + пока меню открыто, клавиши
  // не уходят в игру (иначе стрелки двигали героя, а буквы в фильтре жали OK/отмену).
  window.addEventListener("keydown", function (e) {
    // e.code — чтобы Shift+T работал и в русской раскладке; заглавная «T» в поле ввода — это текст
    var hot = e.shiftKey && !e.ctrlKey && !e.altKey && !e.metaKey && (e.code === "KeyT" || e.key === "T" || e.key === "t");
    if (hot && !isTyping(e)) { e.preventDefault(); e.stopPropagation(); toggle(); return; }
    if (!overlay) return;
    if (e.key === "Escape") { e.preventDefault(); close(); }
    e.stopPropagation();
  }, true);
  ["keyup", "keypress"].forEach(function (n) {
    window.addEventListener(n, function (e) { if (overlay) e.stopPropagation(); }, true);
  });
})();
