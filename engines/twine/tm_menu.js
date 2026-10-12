/* Twine / SugarCube — адаптер данных для общего UI-ядра (_shared/tm_menu_core.js).
   Инжектор склеивает этот адаптер + ядро в один <script>. */
function tmStoryVars() {
  if (window.SugarCube && SugarCube.State && SugarCube.State.variables) return SugarCube.State.variables;
  if (window.State && State.variables) return State.variables;
  return null;
}

window.TM_ADAPTER = {
  accent: "#38e0c8",
  title: "Twine | SugarCube",
  ready: function () { return !!tmStoryVars(); },

  stats: function () {
    var v = tmStoryVars();
    if (!v) return [];
    var rows = Object.keys(v).sort().map(function (k) {
      var t = typeof v[k];
      var type = t === "number" ? "num" : t === "boolean" ? "bool" : t === "string" ? "str" : null;
      if (!type) return null;
      return { name: k, type: type, get: function () { return v[k]; }, set: function (x) { v[k] = x; } };
    }).filter(Boolean);
    return [{ title: T("Переменные истории"), rows: rows }];
  },

  nums: function () {
    var v = tmStoryVars() || {}, o = {};
    Object.keys(v).forEach(function (k) { if (typeof v[k] === "number") o[k] = v[k]; });
    return o;
  },

  actions: function () {
    var v = tmStoryVars();
    return [
      { label: T("Все числовые +100"), run: function () { if (v) Object.keys(v).forEach(function (k) { if (typeof v[k] === "number") v[k] += 100; }); } },
      { label: T("Все флаги = true"), run: function () { if (v) Object.keys(v).forEach(function (k) { if (typeof v[k] === "boolean") v[k] = true; }); } },
      { label: T("Переменные → в консоль"), desc: "console.log(State.variables)", run: function () { console.log("[TM] State.variables:", v); } },
      { label: T("Своя команда (JS)…"), desc: T("доступна vars = State.variables"), run: function () { var c = prompt("JS:", "vars.money += 100"); if (c) (function (vars) { eval(c); })(v); } }
    ];
  },

  footMissing: T("SugarCube не обнаружен — этот PoC рассчитан на SugarCube-истории.")
};
