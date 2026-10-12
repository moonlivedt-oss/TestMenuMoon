// TestMenuMoon для Unity (IL2CPP, BepInEx 6). Окно в игре: Shift+T / F9, Esc — закрыть.
// Находит объекты игры (компоненты и синглтоны из Assembly-CSharp), показывает их числа,
// флаги и строки с понятными именами (словарь tm_words.json — тот же, что у Ren'Py/Godot),
// правка, заморозка, поиск «снимок → сужение». Пока окно открыто — игра на паузе
// (Time.timeScale = 0), клики по интерфейсу игры перекрыты.
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Reflection;
using System.Text.Json;
using BepInEx;
using BepInEx.Logging;
using BepInEx.Unity.IL2CPP;
using Il2CppInterop.Runtime;
using Il2CppInterop.Runtime.InteropTypes;
using Il2CppInterop.Runtime.Runtime;
using UnityEngine;

namespace TestMenu
{
    [BepInPlugin("testmenumoon.unity", "TestMenu", "1.0.0")]
    public class Plugin : BasePlugin
    {
        internal static ManualLogSource L;
        internal static string Dir;

        public override void Load()
        {
            L = Log;
            Dir = Path.GetDirectoryName(typeof(Plugin).Assembly.Location);
            Words.Load(Path.Combine(Dir, "tm_words.json"));
            AddComponent<MenuBehaviour>();
            L.LogInfo("TestMenu: Shift+T / F9");
        }
    }

    // ------------------------------------------------------------------ словарь имён
    internal static class Words
    {
        static Dictionary<string, string> words = new();
        static HashSet<string> generic = new();
        static HashSet<string> inflect = new();
        static HashSet<string> stems = new();
        static List<string> statWords = new();

        public static void Load(string path)
        {
            try
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(path));
                var r = doc.RootElement;
                foreach (var p in r.GetProperty("words").EnumerateObject()) words[p.Name] = p.Value.GetString();
                foreach (var x in r.GetProperty("generic").EnumerateArray()) generic.Add(x.GetString());
                foreach (var x in r.GetProperty("inflect").EnumerateArray()) inflect.Add(x.GetString());
                foreach (var x in r.GetProperty("stems").EnumerateArray()) stems.Add(x.GetString());
                if (r.TryGetProperty("stat_words", out var sw))
                    foreach (var x in sw.EnumerateArray()) statWords.Add(x.GetString());
            }
            catch (Exception e) { Plugin.L?.LogWarning("tm_words.json: " + e.Message); }
        }

        public static List<string> Tokens(string s)
        {
            s = s ?? "";
            if (s.StartsWith("<") && s.Contains(">k__BackingField")) s = s.Substring(1, s.IndexOf('>') - 1);
            if (s.EndsWith("_k__BackingField")) s = s.Substring(0, s.Length - 16).TrimStart('_');
            if (s.StartsWith("m_")) s = s.Substring(2);
            var sb = new System.Text.StringBuilder();
            for (int i = 0; i < s.Length; i++)
            {
                char c = s[i];
                if (i > 0 && char.IsUpper(c) && (char.IsLower(s[i - 1]) || char.IsDigit(s[i - 1]))) sb.Append(' ');
                sb.Append(char.IsLetterOrDigit(c) ? char.ToLowerInvariant(c) : ' ');
            }
            return sb.ToString().Split(' ', StringSplitOptions.RemoveEmptyEntries)
                .Where(t => !t.All(char.IsDigit)).ToList();
        }

        // похоже на стат игрока: слово-стат в начале или конце части имени (alice_love, playerMoney)
        public static bool IsStat(string name)
        {
            foreach (var t in Tokens(name))
                foreach (var w in statWords)
                    if (t.StartsWith(w) || t.EndsWith(w)) return true;
            return false;
        }

        public static string Word(string tok)
        {
            if (words.TryGetValue(tok, out var w)) return w;
            string best = null;
            foreach (var k in words.Keys)
                if (k.Length >= 4 && tok.StartsWith(k) && (best == null || k.Length > best.Length)
                    && (stems.Contains(k) || inflect.Contains(tok.Substring(k.Length))))
                    best = k;
            return best != null ? words[best] : null;
        }

        // (подпись, понятно ли хоть одно слово)
        public static (string, bool) Nice(string name)
        {
            var outp = new List<string>();
            bool hit = false;
            foreach (var t in Tokens(name))
            {
                if (generic.Contains(t)) continue;
                var w = Word(t);
                hit |= w != null;
                outp.Add(w ?? t);
            }
            var title = string.Join(" ", outp);
            if (title.Length == 0) title = name;
            return (char.ToUpper(title[0]) + title.Substring(1), hit);
        }
    }

    // ------------------------------------------------------------------ данные игры
    internal class Entry
    {
        public string Group;        // объект: «GameManager», «Player (Amy)»
        public string Path;         // «GameManager.money» — ключ заморозки/поиска
        public string Name;         // понятное имя поля
        public bool Sure;
        public bool Stat;           // похоже на стат игрока (деньги, симпатия…) — для сортировки групп
        public bool Reverted;       // после правки игра вернула старое — это копия, оригинал в другом месте
        public string OwnerType;    // класс объекта, где лежит поле (GameVariables, Flag…)
        public bool Ui;             // поле объекта интерфейса (Gui/Panel/View…) — обычно копия для экрана
        public object CheckValue;
        public float CheckAt = -1;
        public object Owner;        // null — статическое
        public UnityEngine.Object Root;   // объект сцены/ассет, которому принадлежит поле (null — статика/данные)
        public PropertyInfo Prop;
        public Type Type;

        // объект уничтожен (смена сцены, выгрузка ассетов игрой) — его поля больше не трогаем:
        // чтение/запись в выгруженный объект роняло игру
        public bool Alive()
        {
            if (ReferenceEquals(Root, null)) return true;
            try { return Root != null; } catch { return false; }
        }

        public object Get()
        {
            if (!Alive()) return null;
            try { return Prop.GetValue(Owner); } catch { return null; }
        }

        public bool Set(object v)
        {
            if (!Alive()) return false;
            try
            {
                object val = Type.IsEnum ? (v != null && v.GetType() == Type ? v : Enum.ToObject(Type, Convert.ToInt64(v)))
                    : Type == typeof(int) ? Convert.ToInt32(v) : Type == typeof(float) ? Convert.ToSingle(v)
                    : Type == typeof(double) ? Convert.ToDouble(v) : Type == typeof(long) ? Convert.ToInt64(v)
                    : Type == typeof(bool) ? Convert.ToBoolean(v) : (object)Convert.ToString(v);
                Prop.SetValue(Owner, val);
                CheckValue = val;
                CheckAt = Time.realtimeSinceStartup + 0.6f;   // через 0.6 с (реального времени) проверить
                return true;
            }
            catch (Exception e) { Plugin.L.LogWarning($"{Path}: {e.Message}"); return false; }
        }

        public bool IsNum => Type == typeof(int) || Type == typeof(float) || Type == typeof(double) || Type == typeof(long);
    }

    internal static class Scanner
    {
        static readonly Type[] Prims = { typeof(int), typeof(float), typeof(double), typeof(long), typeof(bool), typeof(string) };
        static HashSet<Assembly> game;
        static Dictionary<string, Type> byIl2CppName;

        // сторонние библиотеки и движок — не «код игры»
        static readonly string[] Skip = {
            "UnityEngine", "Unity.", "Il2Cpp", "System", "mscorlib", "Mono.", "netstandard", "__Generated",
            "DOTween", "Newtonsoft", "UniTask", "Live2D", "BouncyCastle", "Melanchall", "NVorbis", "ZString",
            "Coffee.", "HSVPicker", "KinoBloom", "SimpleFileBrowser", "UiGradient", "UnityUIExtensions", "CFXR",
            "MikeSchweitzer", "F23.", "EditorAttributes", "AttributesSamples", "MemInfo", "Rectpack", "Zalgo",
            "Sirenix", "Rewired", "Spine", "Photon", "Mirror", "FMOD", "Steamworks", "Facepunch", "Discord",
            "LeanTween", "I2.", "Cinemachine", "TextMeshPro", "Assembly-CSharp-firstpass", "AGUI", "AutoTranslate",
            "AdvancedBuilder", "Microsoft", "Google", "Firebase", "Sentry", "websocket", "Lean", "MoreMountains",
        };

        static HashSet<Assembly> Game()
        {
            if (game != null) return game;
            game = new HashSet<Assembly>();
            foreach (var a in AppDomain.CurrentDomain.GetAssemblies())
            {
                string loc;
                try { loc = a.Location ?? ""; } catch { continue; }
                var n = a.GetName().Name ?? "";
                if (loc.Replace('\\', '/').IndexOf("/interop/", StringComparison.OrdinalIgnoreCase) < 0) continue;
                if (Skip.Any(x => n.StartsWith(x, StringComparison.OrdinalIgnoreCase))) continue;
                game.Add(a);
            }
            Plugin.L.LogInfo("сборки игры: " + string.Join(", ", game.Select(a => a.GetName().Name)));
            return game;
        }

        internal static IEnumerable<Type> GameTypes()
        {
            var all = new List<Type>();
            foreach (var a in Game())
            {
                try { all.AddRange(a.GetTypes()); }
                catch (ReflectionTypeLoadException e) { all.AddRange(e.Types.Where(t => t != null)); }
            }
            // без служебных классов компилятора (<PrivateImplementationDetails>, <>c, лямбды):
            // их «статические поля» — сырые блоки данных, чтение роняло игру
            return all.Where(t => t.IsClass && !t.IsAbstract && !t.ContainsGenericParameters && !t.Name.Contains("<")
                && !t.Name.Contains("PrivateImplementationDetails") && !t.Name.StartsWith("_") && !t.Name.Contains("__")
                && !(t.FullName ?? "").Contains("+<") && !(t.FullName ?? "").Contains("c__")
                // сгенерированный движком код внутри сборки игры (Unity.Entities…): статика — не данные игры
                && !NsSkip.Any(x => (t.Namespace ?? "").StartsWith(x)));
        }

        static readonly string[] NsSkip = { "Unity", "UnityEngine", "System", "Microsoft", "TMPro", "Cysharp", "DG." };

        static bool IsGameType(Type t) => t != null && Game().Contains(t.Assembly);

        static Dictionary<string, Type> Map()
        {
            if (byIl2CppName != null) return byIl2CppName;
            byIl2CppName = new Dictionary<string, Type>();
            foreach (var t in GameTypes())
            {
                if (!typeof(MonoBehaviour).IsAssignableFrom(t)) continue;
                try { byIl2CppName[Il2CppType.From(t).FullName] = t; } catch { }
            }
            return byIl2CppName;
        }

        internal static object Cast(Il2CppObjectBase o, Type t)
        {
            try { return typeof(Il2CppObjectBase).GetMethod("TryCast").MakeGenericMethod(t).Invoke(o, null); }
            catch { return null; }
        }

        // свойства-поля типа и его игровых базовых классов
        static IEnumerable<PropertyInfo> Fields(Type t, bool stat)
        {
            var flags = BindingFlags.Public | BindingFlags.DeclaredOnly | (stat ? BindingFlags.Static : BindingFlags.Instance);
            // только настоящие поля IL2CPP: у них в interop-типе есть NativeFieldInfoPtr_<имя>,
            // геттер читает память и не запускает код игры (свойства игры могли падать)
            for (var c = t; c != null && IsGameType(c); c = c.BaseType)
                foreach (var p in c.GetProperties(flags))
                    if (p.CanRead && p.CanWrite && p.GetIndexParameters().Length == 0 && p.GetGetMethod() != null
                        && c.GetField("NativeFieldInfoPtr_" + p.Name, BindingFlags.NonPublic | BindingFlags.Static) != null)
                        yield return p;
        }

        public static string Diag = "";
        const int MaxInstances = 25;
        const int MaxPerObject = 20;
        const int MaxDepth = 3;
        static readonly string TracePath = Environment.GetEnvironmentVariable("TM_TRACE");

        static void Trace(string msg)
        {
            if (!string.IsNullOrEmpty(TracePath)) File.AppendAllText(TracePath, msg + Environment.NewLine);
        }

        // класс уже инициализирован самой игрой? Раньше меню запускало статические конструкторы
        // всех классов игры (il2cpp_runtime_class_init) — код игры выполнялся не вовремя, это могло ронять игру
        static unsafe bool Initialized(Type t)
        {
            try
            {
                var ptr = Il2CppClassPointerStore.GetNativeClassPointer(t);
                if (ptr == IntPtr.Zero) return false;
                return UnityVersionHandler.Wrap((Il2CppClass*)ptr).InitializedAndNoError;
            }
            catch { return false; }
        }

        static UnityEngine.Object RootOf(object o)
        {
            try { return (o as Il2CppObjectBase)?.TryCast<UnityEngine.Object>(); } catch { return null; }
        }

        public static List<Entry> Collect()
        {
            var outp = new List<Entry>();
            var seen = new HashSet<IntPtr>();
            visited.Clear();
            if (Game().Count == 0) { Plugin.L.LogWarning("сборки игры не найдены"); return outp; }

            // 1) синглтоны и статические значения игровых классов
            foreach (var t in GameTypes())
            {
                var statics = Fields(t, true).ToList();
                if (statics.Count == 0) continue;
                if (!Initialized(t)) continue;  // статика неинициализированного класса — пустая память
                Trace("static " + t.FullName);
                foreach (var p in statics)
                {
                    try
                    {
                        if (Prims.Contains(p.PropertyType) && !IsConstName(p.Name)) Add(outp, t.Name + " (static)", t.Name, null, p, null);
                        else if (IsGameType(p.PropertyType))   // Instance, _instance, Current, Main…
                        {
                            var o = p.GetValue(null);
                            if (o is Il2CppObjectBase b && seen.Add(b.Pointer))
                                AddObject(outp, o, p.PropertyType == t ? t.Name : t.Name + "." + p.Name, 0, RootOf(o));
                        }
                    }
                    catch { }
                }
            }
            // 2) живые компоненты игры в загруженных сценах
            var map = Map();
            var all = Resources.FindObjectsOfTypeAll(Il2CppType.Of<MonoBehaviour>());
            // типы с десятками экземпляров — элементы сцены (команды сценария, кнопки), не состояние игры
            // …и объекты-носители сотен компонентов (Flowchart Fungus: по компоненту на команду сценария)
            var perType = new Dictionary<string, int>();
            var perGo = new Dictionary<int, int>();
            foreach (var mb in all)
            {
                try
                {
                    var n = mb.GetIl2CppType().FullName;
                    perType[n] = perType.TryGetValue(n, out var c) ? c + 1 : 1;
                    var go = mb.TryCast<MonoBehaviour>()?.gameObject;
                    if (go != null) { var id = go.GetInstanceID(); perGo[id] = perGo.TryGetValue(id, out var g) ? g + 1 : 1; }
                }
                catch { }
            }
            foreach (var mb in all)
            {
                try
                {
                    if (mb == null || seen.Contains(mb.Pointer)) continue;
                    var comp = mb.TryCast<MonoBehaviour>();
                    if (comp == null || !comp.gameObject.scene.IsValid()) continue;   // префабы-ассеты не трогаем
                    if (perGo.TryGetValue(comp.gameObject.GetInstanceID(), out var onGo) && onGo > MaxPerObject) continue;
                    var il2name = mb.GetIl2CppType().FullName;
                    if (perType.TryGetValue(il2name, out var cnt) && cnt > MaxInstances) continue;
                    if (!map.TryGetValue(il2name, out var t)) continue;
                    Trace("object " + t.FullName);
                    var o = Cast(mb, t);
                    if (o == null) continue;
                    seen.Add(mb.Pointer);
                    var go = comp.gameObject.name;
                    AddObject(outp, o, t.Name == go ? t.Name : $"{t.Name} ({go})", 0, comp);
                }
                catch { }
            }
            // 3) ScriptableObject игры (данные-ассеты: статы, предметы, настройки баланса)
            int so = 0;
            try
            {
                var soMap = new Dictionary<string, Type>();
                foreach (var t in GameTypes())
                    if (typeof(ScriptableObject).IsAssignableFrom(t))
                        try { soMap[Il2CppType.From(t).FullName] = t; } catch { }
                var sos = Resources.FindObjectsOfTypeAll(Il2CppType.Of<ScriptableObject>());
                var soPer = new Dictionary<string, int>();
                foreach (var o in sos)
                    try { var n = o.GetIl2CppType().FullName; soPer[n] = soPer.TryGetValue(n, out var c) ? c + 1 : 1; } catch { }
                foreach (var o in sos)
                {
                    try
                    {
                        var n = o.GetIl2CppType().FullName;
                        if (!soMap.TryGetValue(n, out var t) || soPer[n] > MaxInstances || !seen.Add(o.Pointer)) continue;
                        var obj = Cast(o, t);
                        if (obj == null) continue;
                        Trace("asset " + t.FullName);
                        AddObject(outp, obj, $"{t.Name} [{o.name}] (данные)", 0, o);
                        so++;
                    }
                    catch { }
                }
            }
            catch (Exception e) { Plugin.L.LogWarning("ScriptableObject: " + e.Message); }
            Diag = $"gameTypes={GameTypes().Count()} mbTypes={map.Count} statics={outp.Count(e => e.Owner == null)} objects={seen.Count} assets={so}";
            return outp;
        }

        // ИМЕНА_ЗАГЛАВНЫМИ — константы/настройки движка, игроку не нужны
        static bool IsConstName(string n) => n.Length > 2 && n.Any(char.IsLetter) && !n.Any(char.IsLower);

        static HashSet<IntPtr> visited = new();

        static void AddObject(List<Entry> outp, object o, string group, int depth, UnityEngine.Object root)
        {
            if (o is Il2CppObjectBase ob && depth > 0 && !visited.Add(ob.Pointer)) return;
            // переменная Fungus (IntegerVariable, FloatVariable…): ключ + value -> одна строка с именем ключа
            var tt = o.GetType();
            if (tt.Name.EndsWith("Variable"))
            {
                var keyP = Fields(tt, false).FirstOrDefault(p => p.Name == "key" && p.PropertyType == typeof(string));
                var valP = Fields(tt, false).FirstOrDefault(p => p.Name == "value" && Prims.Contains(p.PropertyType));
                if (keyP != null && valP != null)
                {
                    var key = keyP.GetValue(o) as string;
                    if (!string.IsNullOrEmpty(key))
                    {
                        var (nm, sure) = Words.Nice(key);
                        outp.Add(new Entry { Group = "Переменные сценария (Fungus)", Path = "fungus." + key, Name = nm, Sure = sure,
                            Stat = true, Owner = o, Root = root, Prop = valP, Type = valP.PropertyType });
                        return;
                    }
                }
            }
            foreach (var p in Fields(o.GetType(), false))
            {
                try
                {
                    if (Prims.Contains(p.PropertyType) || p.PropertyType.IsEnum) Add(outp, group, group, o, p, root);
                    else if (IsList(p.PropertyType, out var elem) && depth < MaxDepth)
                        AddList(outp, p.GetValue(o), elem, group + "." + Clean(p.Name), root);
                    else if (depth < MaxDepth && IsGameType(p.PropertyType) && !typeof(UnityEngine.Object).IsAssignableFrom(p.PropertyType))
                    {
                        var sub = p.GetValue(o);        // вложенный объект данных (stats, inventory…)
                        if (sub != null) AddObject(outp, sub, group + "." + Clean(p.Name), depth + 1, root);
                    }
                }
                catch { }
            }
        }

        // имя поля для подписи группы: без _k__BackingField и ведущих «_»
        static string Clean(string n)
        {
            if (n.EndsWith("_k__BackingField")) n = n.Substring(0, n.Length - 16);
            return n.TrimStart('_');
        }

        static readonly string[] UiWords = { "Gui", "GUI", "Ui", "UI", "Panel", "View", "Popup", "Widget", "Button", "Hud", "HUD",
            "Display", "Text", "Window", "Tooltip", "Slider", "Menu", "Screen", "Canvas" };

        static bool IsUiType(Type t) => t != null && UiWords.Any(w => t.Name.Contains(w));

        static void Add(List<Entry> outp, string group, string prefix, object owner, PropertyInfo p, UnityEngine.Object root, string label = null)
        {
            var (name, sure) = Words.Nice(p.Name);
            if (label != null) name = label + "  |  " + name;
            var ot = owner?.GetType() ?? p.DeclaringType;
            outp.Add(new Entry { Group = group, Path = prefix + "." + p.Name, Name = name, Sure = sure || label != null,
                Stat = p.PropertyType != typeof(string) && !p.PropertyType.IsEnum && Words.IsStat(p.Name),
                Owner = owner, Root = root, Prop = p, Type = p.PropertyType, OwnerType = ot.Name, Ui = IsUiType(ot) });
        }

        // ---- списки Il2CppSystem.Collections.Generic.List<T> из объектов игры: флаги, предметы…
        const int MaxListItems = 200;

        static bool IsList(Type t, out Type elem)
        {
            elem = null;
            if (!t.IsGenericType) return false;
            var def = t.GetGenericTypeDefinition().FullName ?? "";
            if (def != "Il2CppSystem.Collections.Generic.List`1") return false;
            elem = t.GenericTypeArguments[0];
            return IsGameType(elem) && !typeof(UnityEngine.Object).IsAssignableFrom(elem);
        }

        static readonly string[] LabelFields = { "name", "_name", "Name", "key", "_key", "id", "_id", "title", "displayName", "gameId", "_gameId" };

        // подпись элемента: строковое поле name/key/id… или имя ассета (prefab, data) — Item -> «Пицца»
        static string ItemLabel(object el, int i)
        {
            var t = el.GetType();
            foreach (var f in LabelFields)
            {
                var pr = Fields(t, false).FirstOrDefault(x => x.Name == f && x.PropertyType == typeof(string));
                if (pr != null && pr.GetValue(el) is string sv && sv.Length > 0) return sv;
            }
            foreach (var pr in Fields(t, false))
                if (typeof(UnityEngine.Object).IsAssignableFrom(pr.PropertyType))
                {
                    try { if (pr.GetValue(el) is UnityEngine.Object uo && uo != null && !string.IsNullOrEmpty(uo.name)) return uo.name; }
                    catch { }
                }
            return "#" + (i + 1);
        }

        static void AddList(List<Entry> outp, object list, Type elem, string group, UnityEngine.Object root)
        {
            if (list == null) return;
            var lt = list.GetType();
            int count = (int)(lt.GetProperty("Count")?.GetValue(list) ?? 0);
            var get = lt.GetMethod("get_Item", new[] { typeof(int) });
            if (get == null || count == 0) return;
            var fields = Fields(elem, false).Where(f => Prims.Contains(f.PropertyType) || f.PropertyType.IsEnum)
                .Where(f => !LabelFields.Contains(f.Name)).ToList();
            if (fields.Count == 0) return;
            for (int i = 0; i < Math.Min(count, MaxListItems); i++)
            {
                object el;
                try { el = get.Invoke(list, new object[] { i }); } catch { continue; }
                if (el == null) continue;
                var label = ItemLabel(el, i);
                foreach (var f in fields)
                    Add(outp, group, $"{group}[{i}]", el, f, root, label);
            }
        }
    }

    // ------------------------------------------------------------------ мышь
    // В части игр (Input System only) до IMGUI не доходят события мыши: кнопки не нажимались.
    // Опрашиваем мышь сами: старый Input, если он включён, иначе Mouse.current нового Input System.
    internal static class MouseIn
    {
        static bool legacyOk = true;
        static bool triedIS;
        static PropertyInfo isCurrent;

        static object IsMouse()
        {
            if (!triedIS)
            {
                triedIS = true;
                foreach (var a in AppDomain.CurrentDomain.GetAssemblies())
                {
                    if (a.GetName().Name != "Unity.InputSystem") continue;
                    var t = a.GetType("UnityEngine.InputSystem.Mouse");
                    isCurrent = t?.GetProperty("current", BindingFlags.Public | BindingFlags.Static);
                }
            }
            try { return isCurrent?.GetValue(null); } catch { return null; }
        }

        static object Prop(object o, string name)
        {
            try { return o?.GetType().GetProperty(name)?.GetValue(o); } catch { return null; }
        }

        static Vector2 ReadV2(object control)
        {
            try
            {
                var m = control?.GetType().GetMethod("ReadValue", Type.EmptyTypes);
                return m != null ? (Vector2)m.Invoke(control, null) : Vector2.zero;
            }
            catch { return Vector2.zero; }
        }

        // позиция в координатах IMGUI (верх-лево), нажатие в этом кадре, зажата, прокрутка (щелчки колеса)
        public static bool Poll(out Vector2 pos, out bool pressed, out bool held, out float wheel)
        {
            pos = Vector2.zero; pressed = held = false; wheel = 0;
            if (legacyOk)
            {
                try
                {
                    var mp = Input.mousePosition;
                    pos = new Vector2(mp.x, Screen.height - mp.y);
                    pressed = Input.GetMouseButtonDown(0);
                    held = Input.GetMouseButton(0);
                    wheel = Input.mouseScrollDelta.y;
                    return true;
                }
                catch { legacyOk = false; }
            }
            var mouse = IsMouse();
            if (mouse == null) return false;
            var p = ReadV2(Prop(mouse, "position"));
            pos = new Vector2(p.x, Screen.height - p.y);
            var lb = Prop(mouse, "leftButton");
            pressed = Prop(lb, "wasPressedThisFrame") is bool b1 && b1;
            held = Prop(lb, "isPressed") is bool b2 && b2;
            wheel = ReadV2(Prop(mouse, "scroll")).y / 120f;
            return true;
        }
    }

    // ------------------------------------------------------------------ время игры
    // Пропуск времени через метод самой игры, если он есть: GameScript.PassTimeInstantly(минуты, StaminaSyncType)
    // (встречается в симуляторах жизни). Игра сама прогоняет минуты: голод, усталость, события, аренда.
    internal static class GameTime
    {
        static bool searched;
        static Type gsType, gvType;
        static MethodInfo pass;
        static PropertyInfo gvProp, stateProp, timeProp;
        static UnityEngine.Object gsRoot;
        static object gs;

        public const int Normal = 0, Recovery = 2;      // StaminaSyncType: Normal — как обычно, Recovery — как во сне

        static void Find()
        {
            if (searched) return;
            searched = true;
            try
            {
                foreach (var t in Scanner.GameTypes())
                {
                    var m = t.GetMethod("PassTimeInstantly", BindingFlags.Public | BindingFlags.Instance);
                    var ps = m?.GetParameters();
                    if (ps == null || ps.Length != 2 || ps[0].ParameterType != typeof(int) || !ps[1].ParameterType.IsEnum) continue;
                    if (!typeof(MonoBehaviour).IsAssignableFrom(t)) continue;
                    gsType = t;
                    pass = m;
                    gvProp = t.GetProperty("GameVariables");
                    stateProp = t.GetProperty("GameState");
                    gvType = gvProp?.PropertyType;
                    timeProp = gvType?.GetProperty("time");
                    if (timeProp != null && timeProp.PropertyType != typeof(int)) timeProp = null;
                    break;
                }
            }
            catch (Exception e) { Plugin.L.LogWarning("GameTime: " + e.Message); }
        }

        static object Instance()
        {
            Find();
            if (gsType == null) return null;
            try
            {
                if (gs != null && gsRoot != null) return gs;
                gs = null;
                foreach (var o in Resources.FindObjectsOfTypeAll(Il2CppType.From(gsType)))
                {
                    var mb = o.TryCast<MonoBehaviour>();
                    if (mb == null || !mb.gameObject.scene.IsValid()) continue;
                    gs = Scanner.Cast(o, gsType);
                    gsRoot = mb;
                    if (gs != null) break;
                }
            }
            catch { gs = null; }
            return gs;
        }

        public static bool Supported { get { Find(); return pass != null; } }

        // текущее время в минутах или -1
        public static int Now()
        {
            try
            {
                var g = Instance();
                var gv = g != null && gvProp != null ? gvProp.GetValue(g) : null;
                return gv != null && timeProp != null ? (int)timeProp.GetValue(gv) : -1;
            }
            catch { return -1; }
        }

        static object CallStatic(string name, params object[] args)
        {
            try
            {
                var m = gvType?.GetMethods(BindingFlags.Public | BindingFlags.Static)
                    .FirstOrDefault(x => x.Name == name && x.GetParameters().Length == args.Length
                        && x.GetParameters().All(p => p.ParameterType == typeof(int)));
                return m?.Invoke(null, args);
            }
            catch { return null; }
        }

        // «День 4, 16:29» — функциями самой игры (TimeToDay / TimeToHourString), иначе по 1440 минут в сутках
        public static string Describe(int t)
        {
            if (t < 0) return "";
            var day = CallStatic("TimeToDay", t) ?? t / 1440;
            var hour = CallStatic("TimeToHourString", t) as string ?? $"{t % 1440 / 60:00}:{t % 60:00}";
            return $"День {day}, {hour}";
        }

        // минут до следующего утра (hour:00)
        public static int MinutesToMorning(int t, int hour)
        {
            if (t < 0) return 0;
            if (CallStatic("TimeToDay", t) is int day && CallStatic("TimeFromDate", day, hour, 0) is int today)
            {
                int target = t < today ? today : CallStatic("TimeFromDate", day + 1, hour, 0) is int tm ? tm : today + 1440;
                return target - t;
            }
            int inDay = t % 1440, h = hour * 60;
            return inDay < h ? h - inDay : 1440 - inDay + h;
        }

        // почему пропуск сейчас нельзя («» — можно): во время сцены/мини-игры игра не ждёт смены времени
        public static string Blocked()
        {
            var g = Instance();
            if (g == null || Now() < 0) return "Загрузи сохранение — тогда можно будет пропускать время";
            try
            {
                var st = stateProp?.GetValue(g) as Il2CppSystem.Object;
                var name = st?.GetIl2CppType().Name ?? "";
                if (name != "" && !name.Contains("Room")) return "Только в комнате (сейчас идёт сцена или мини-игра)";
            }
            catch { }
            return "";
        }

        public static void Pass(int minutes, int stamina)
        {
            try
            {
                var g = Instance();
                if (g == null || minutes <= 0) return;
                var before = Now();
                pass.Invoke(g, new object[] { minutes, Enum.ToObject(pass.GetParameters()[1].ParameterType, stamina) });
                Plugin.L.LogInfo($"пропуск времени: {Describe(before)} -> {Describe(Now())} ({minutes} мин)");
            }
            catch (Exception e) { Plugin.L.LogWarning("пропуск времени: " + (e.InnerException ?? e).Message); }
        }
    }

    // ------------------------------------------------------------------ окно
    // Компонент Unity — только Update/OnGUI. Вся логика — в обычном классе MenuCore: Il2CppInterop
    // переносит в IL2CPP каждый метод компонента и на части сигнатур (кортежи, локальные функции)
    // падал, плагин не загружался.
    public class MenuBehaviour : MonoBehaviour
    {
        public MenuBehaviour(IntPtr ptr) : base(ptr) { }
        static readonly MenuCore core = new MenuCore();
        void Update() => core.Update();
        void OnGUI() => core.OnGUI();
    }

    internal class MenuCore
    {

        bool open;
        float prevScale = 1f;
        float speed = 1f;                                   // темп игры из вкладки «Игра»
        Dictionary<string, JsonElement> pendingProfile;     // заморозки профиля, ещё не найденные в игре
        float profileNext = 10f, profileUntil = 600f;
        readonly List<(string Name, Vector3 Pos)> places = new();
        string tab = "main";
        HashSet<string> favs;       // избранное (пути полей), файл favorites.json рядом с плагином
        string filter = "";
        int step = 1;
        List<Entry> entries = new();
        Dictionary<string, object> frozen = new();
        HashSet<string> expanded = new();
        bool showOther;
        Dictionary<string, double> snap = new();
        List<string> cands = new();
        string scanMsg = "Нажми «Снимок», поиграй и возвращайся сужать.";
        string tip = "";
        List<(string Key, List<Entry> Items, int Stats)> groupsCache;
        string groupsKey;
        int groupsVer, entriesVer;
        float k = 1f;

        GUIStyle sBad, sWin, sShade, sHead, sHeadBg, sText, sDim, sAcc, sBtn, sBtnOn, sField, sFieldOn, sRow, sThumb, sGroup;
        static readonly Color Bg = new Color(0.063f, 0.078f, 0.114f, 1f), Bg3 = new Color(0.118f, 0.141f, 0.196f, 1f),
            Acc = new Color(0.22f, 0.878f, 0.784f, 1f), Txt = new Color(0.906f, 0.922f, 0.949f, 1f), Dim = new Color(0.545f, 0.576f, 0.639f, 1f);

        static Texture2D Tex(Color c)
        {
            var t = new Texture2D(1, 1);
            t.SetPixel(0, 0, c);
            t.Apply();
            t.hideFlags = HideFlags.HideAndDontSave;
            return t;
        }

        void Styles()
        {
            if (sWin != null && Mathf.Approximately(k, Screen.height / 1080f)) return;
            k = Mathf.Clamp(Screen.height / 1080f, 0.6f, 2f);
            int fs(float x) => Mathf.RoundToInt(x * k);
            sWin = new GUIStyle(GUI.skin.box);
            sWin.normal.background = Tex(Bg);
            sShade = new GUIStyle(GUI.skin.box);
            sShade.normal.background = Tex(new Color(0.02f, 0.03f, 0.05f, 0.65f));
            sHead = new GUIStyle(GUI.skin.label) { fontSize = fs(24), fontStyle = FontStyle.Bold };
            sHead.normal.textColor = new Color(0.03f, 0.07f, 0.06f);
            sText = new GUIStyle(GUI.skin.label) { fontSize = fs(18), clipping = TextClipping.Clip };
            sText.normal.textColor = Txt;
            sDim = new GUIStyle(sText) { fontSize = fs(13) };
            sDim.normal.textColor = Dim;
            sAcc = new GUIStyle(sText) { fontStyle = FontStyle.Bold };
            sAcc.normal.textColor = Acc;
            sBtn = new GUIStyle(GUI.skin.button) { fontSize = fs(16) };
            sBtn.normal.background = Tex(Bg3);
            sBtn.hover.background = Tex(Acc);
            sBtn.active.background = Tex(Acc);
            sBtn.normal.textColor = Txt;
            sBtn.hover.textColor = new Color(0.03f, 0.07f, 0.06f);
            sBtnOn = new GUIStyle(sBtn);
            sBtnOn.normal.background = Tex(Acc);
            sBtnOn.normal.textColor = new Color(0.03f, 0.07f, 0.06f);
            sField = new GUIStyle(sBtn) { alignment = TextAnchor.MiddleLeft };
            sField.normal.background = Tex(new Color(0.04f, 0.05f, 0.08f, 1f));
            sField.hover.background = Tex(new Color(0.09f, 0.11f, 0.16f, 1f));
            sField.hover.textColor = Txt;
            sFieldOn = new GUIStyle(sField);
            sFieldOn.normal.background = Tex(new Color(0.12f, 0.25f, 0.24f, 1f));
            sFieldOn.hover.background = sFieldOn.normal.background;
            sRow = new GUIStyle(GUI.skin.box);
            sRow.normal.background = Tex(new Color(1, 1, 1, 0.03f));
            sThumb = new GUIStyle(GUI.skin.box);
            sThumb.normal.background = Tex(Acc);
            sHeadBg = new GUIStyle(GUI.skin.box);
            sHeadBg.normal.background = Tex(Acc);
            sGroup = new GUIStyle(sBtn) { alignment = TextAnchor.MiddleLeft, fontStyle = FontStyle.Bold };
            sGroup.normal.textColor = Acc;
            sBad = new GUIStyle(sDim);
            sBad.normal.textColor = new Color(1f, 0.42f, 0.42f);
            hoverOf.Clear();
            foreach (var st in new[] { sBtn, sGroup, sField })
            {
                var h = new GUIStyle(st);
                h.normal.background = st == sField ? Tex(new Color(0.09f, 0.11f, 0.16f, 1f)) : Tex(Acc);
                h.normal.textColor = st == sField ? Txt : new Color(0.03f, 0.07f, 0.06f);
                hoverOf[st] = h;
            }
        }

        // ---------------------------------------------------------- открыть / закрыть
        void Toggle(bool on)
        {
            if (on == open) return;
            open = on;
            if (on)
            {
                prevScale = Time.timeScale;
                Time.timeScale = 0f;
                skipMsg = "";
                Refresh();
                ShowBlocker(true);
            }
            else
            {
                Time.timeScale = prevScale;
                ShowBlocker(false);
                focusId = null;
                Release();
            }
        }

        // меню закрыто — не держим ссылки на тысячи объектов игры (кроме замороженных):
        // игра выгружает сцены и ассеты, а удержанные объекты потом читались уже выгруженными
        void Release()
        {
            entries = frozen.Count == 0 ? new List<Entry>() : entries.Where(e => frozen.ContainsKey(e.Path)).ToList();
            entriesVer++;
            groupsCache = null;
            mFav = new(); mFungus = new(); mBest = default; mLists = new(); mainVer = -1;
        }

        // клики по интерфейсу игры: на время меню выключаем модуль ввода EventSystem (uGUI).
        // Саму EventSystem не выключаем: без неё EventSystem.current == null и код игры
        // (UIManager.IsPointerOverGameObject) сыпал NullReferenceException каждый кадр
        UnityEngine.EventSystems.BaseInputModule pausedModule;

        void ShowBlocker(bool on)
        {
            try
            {
                if (on)
                {
                    var es = UnityEngine.EventSystems.EventSystem.current;
                    var m = es != null ? es.currentInputModule : null;
                    if (m != null && m.enabled) { m.enabled = false; pausedModule = m; }
                }
                else if (!ReferenceEquals(pausedModule, null))
                {
                    if (pausedModule != null) pausedModule.enabled = true;   // мог быть уничтожен сменой сцены
                    pausedModule = null;
                }
            }
            catch (Exception e) { Plugin.L.LogWarning("EventSystem: " + e.Message); }
        }

        float selftestAt = -1;
        float guiTestAt = -1;

        // самопроверка с окном: TM_SELFTEST_GUI=<png> — открыть меню, скриншот, выйти
        void GuiTest()
        {
            var png = Environment.GetEnvironmentVariable("TM_SELFTEST_GUI");
            if (string.IsNullOrEmpty(png)) return;
            float t = Time.realtimeSinceStartup;
            if (guiTestAt < 0) guiTestAt = t + 25f;
            if (t < guiTestAt) return;
            if (!open && guiTestAt < float.MaxValue - 10) { Toggle(true); guiTestAt = t + 3f; return; }
            if (open && guiTestAt < float.MaxValue - 10 && tab == "main" && Environment.GetEnvironmentVariable("TM_SELFTEST_CLICK") != null)
            {
                // имитация щелчка по вкладке «Поиск» (та же логика, что у настоящего нажатия)
                bool ok = MouseIn.Poll(out var mp, out _, out _, out _);
                Plugin.L.LogInfo($"selftest: опрос мыши {(ok ? "работает" : "НЕ работает")}, позиция {mp}");
                float w = Mathf.Min(Screen.width * 0.9f, 1150 * k), h = Screen.height * 0.86f;
                float wx = (Screen.width - w) / 2, wy = (Screen.height - h) / 2;
                clickPending = true;
                clickPos = new Vector2(wx + 12 * k + 156 * k + 70 * k, wy + 52 * k + 10 * k + 17 * k);
                guiTestAt = t + 1.5f;
                return;
            }
            if (open && guiTestAt < float.MaxValue - 10) { ScreenCapture.CaptureScreenshot(png); guiTestAt = float.MaxValue - 5; quitAt = t + 3f; return; }
            if (quitAt > 0 && t > quitAt) Application.Quit();
        }
        float quitAt = -1;

        public void Update()
        {
            SelfTest();
            GuiTest();
            ProfileTick();
            // игра сама вернула темп 1 (выход из своей паузы) — снова наш темп
            if (!open && !Mathf.Approximately(speed, 1f) && Mathf.Approximately(Time.timeScale, 1f)) Time.timeScale = speed;
            if (pendingSkip > 0 && !open)
            {
                // пропуск времени — после закрытия меню (игра снята с паузы, сюжетные события запускаются как обычно)
                int m = pendingSkip;
                pendingSkip = 0;
                GameTime.Pass(m, pendingStamina);
            }
            if (open)
            {
                if (MouseIn.Poll(out var pos, out var pressed, out var held, out var wheel))
                {
                    mousePos = pos;
                    holdMouse = held;
                    if (pressed && !imguiClickFrame) { clickPending = true; clickPos = pos; }
                    if (wheel != 0 && viewRect.Contains(pos - Vector2.zero)) scrollY -= wheel * 60f * k;
                }
                imguiClickFrame = false;
                foreach (var e in entries)
                    if (e.CheckAt > 0 && Time.realtimeSinceStartup > e.CheckAt)
                    {
                        e.CheckAt = -1;
                        e.Reverted = !Equals(e.Get(), e.CheckValue);
                        if (e.Reverted) groupsVer = -1;   // пересортировать: копии — вниз
                    }
            }
            if (frozen.Count == 0) return;
            foreach (var e in entries)
                if (frozen.TryGetValue(e.Path, out var v) && !Equals(e.Get(), v)) e.Set(v);
        }

        // самопроверка: TM_SELFTEST=<файл отчёта> — через 20 с собрать объекты, записать, выйти
        void SelfTest()
        {
            var outFile = Environment.GetEnvironmentVariable("TM_SELFTEST");
            if (string.IsNullOrEmpty(outFile)) return;
            if (selftestAt < 0) selftestAt = Time.realtimeSinceStartup + 20f;
            if (Time.realtimeSinceStartup < selftestAt) return;
            selftestAt = float.MaxValue;
            var lines = new List<string>();
            try
            {
                var es = Scanner.Collect();
                lines.Add($"entries: {es.Count}, groups: {es.Select(e => e.Group).Distinct().Count()}");
                lines.Add("diag: " + Scanner.Diag);
                foreach (var g in es.GroupBy(e => e.Group).OrderByDescending(g => g.Count(e => e.Stat)).Take(25))
                    lines.Add($"# {g.Key}: {g.Count(e => e.Stat)} статов из {g.Count()}");
                foreach (var e in es.Where(e => e.Stat).Take(300))
                    lines.Add($"{e.Group} | {e.Path} | {e.Name} | {(e.Sure ? "+" : "?")} | {Fmt(e.Get())}");
            }
            catch (Exception ex) { lines.Add("ERROR " + ex); }
            lines.InsertRange(0, Probe());
            File.WriteAllLines(outFile, lines);
            Application.Quit();
        }

        // какие функции IMGUI есть в сборке игры: вырезанная бросает «unstripping failed» сразу при вызове
        static List<string> Probe()
        {
            var res = new List<string>();
            var r = new Rect(0, 0, 10, 10);
            var tests = new (string, Action)[]
            {
                ("GUI.skin", () => { var _ = GUI.skin; }),
                ("new GUIStyle", () => new GUIStyle()),
                ("GUIStyle(label)", () => new GUIStyle(GUI.skin.label)),
                ("Texture2D.SetPixel", () => { var t = new Texture2D(1, 1); t.SetPixel(0, 0, Color.red); t.Apply(); }),
                ("GUI.Label", () => GUI.Label(r, "x")),
                ("GUI.Label(style)", () => GUI.Label(r, "x", new GUIStyle())),
                ("GUI.Box", () => GUI.Box(r, "")),
                ("GUI.Box(style)", () => GUI.Box(r, "", new GUIStyle())),
                ("GUI.Button(style)", () => GUI.Button(r, "x", new GUIStyle())),
                ("GUI.DrawTexture", () => GUI.DrawTexture(r, Texture2D.whiteTexture)),
                ("GUI.TextField", () => GUI.TextField(r, "x", new GUIStyle())),
                ("GUI.BeginScrollView", () => GUI.BeginScrollView(r, Vector2.zero, r)),
                ("GUI.EndScrollView", () => GUI.EndScrollView()),
                ("GUI.BeginGroup", () => GUI.BeginGroup(r)),
                ("GUI.EndGroup", () => GUI.EndGroup()),
                ("GUI.depth", () => GUI.depth = 0),
                ("GUI.color", () => GUI.color = Color.white),
                ("Event.current", () => { var _ = Event.current; }),
                ("GUIUtility.keyboardControl", () => { var _ = GUIUtility.keyboardControl; }),
                ("Screen.height", () => { var _ = Screen.height; }),
                ("Time.timeScale", () => { var _ = Time.timeScale; }),
            };
            foreach (var (name, act) in tests)
            {
                string st;
                try { act(); st = "ok"; }
                catch (Exception e) { st = e.Message.Contains("unstripping") ? "ВЫРЕЗАНО" : "есть (" + e.GetType().Name + ")"; }
                res.Add($"probe {name}: {st}");
            }
            return res;
        }

        // ---------------------------------------------------------- отрисовка
        // Только то, что не вырезано в сборках игр (проверено зондом): без GUI.DrawTexture,
        // GUI.BeginScrollView/EndScrollView и GUI.TextField — своя прокрутка (BeginGroup + смещение)
        // и своё поле ввода (нажатия клавиш через Event.current).
        float scrollY;
        Rect viewRect;
        Vector2 groupOrigin;        // смещение текущей GUI-группы (клик приходит в экранных координатах)
        bool clickPending;          // нажатие мыши этого кадра — отрабатывается в проходе Repaint
        Vector2 clickPos;
        bool holdMouse;
        Vector2 mousePos;
        bool imguiClickFrame;
        float contentH;
        string focusId;             // поле ввода в фокусе
        string focusBuf = "";
        Action<string> focusCommit;
        bool focusLive;             // фильтр: применять на каждое нажатие

        void Refresh()
        {
            entries = Scanner.Collect();
            entriesVer++;
        }

        public void OnGUI()
        {
            var ev = Event.current;
            if (ev.type == EventType.KeyDown)
            {
                if (open && focusId != null && HandleTyping(ev)) { ev.Use(); return; }
                if (ev.keyCode == KeyCode.F9 || (ev.keyCode == KeyCode.T && ev.shift)) { Toggle(!open); ev.Use(); return; }
                if (open && ev.keyCode == KeyCode.Escape) { Toggle(false); ev.Use(); return; }
                if (open && (ev.keyCode == KeyCode.PageDown || ev.keyCode == KeyCode.PageUp))
                {
                    scrollY += (ev.keyCode == KeyCode.PageDown ? 1 : -1) * viewRect.height * 0.9f;
                    ev.Use();
                }
            }
            if (!open)
            {
                if (!Mathf.Approximately(speed, 1f) && ev.type == EventType.Repaint)
                {
                    Styles();
                    GUI.Box(new Rect(Screen.width - 118 * k, 8 * k, 108 * k, 30 * k), speed == 0f ? "ПАУЗА" : "×" + speed.ToString("0.##"), sBtnOn);
                }
                return;
            }
            if (ev.type == EventType.MouseDown && ev.button == 0)
            {
                clickPending = true;
                clickPos = ev.mousePosition;
                imguiClickFrame = true;
                ev.Use();
            }
            if (ev.type == EventType.ScrollWheel) ev.Use();   // колесо опрашивается в Update
            if (ev.type == EventType.MouseMove || ev.type == EventType.Repaint) { }
            bool repaint = ev.type == EventType.Repaint;
            Styles();
            GUI.depth = -1000;
            GUI.Box(new Rect(0, 0, Screen.width, Screen.height), "", sShade);
            float w = Mathf.Min(Screen.width * 0.9f, 1150 * k), h = Screen.height * 0.86f;
            var win = new Rect((Screen.width - w) / 2, (Screen.height - h) / 2, w, h);
            GUI.Box(win, "", sWin);
            // шапка: рамка с цветным фоном (GUI.DrawTexture в части игр вырезан)
            var head = new Rect(win.x, win.y, w, 52 * k);
            GUI.Box(head, "", sHeadBg);
            GUI.Label(new Rect(head.x + 18 * k, head.y + 10 * k, w * 0.6f, 34 * k), "TEST MENU  |  " + Application.productName, sHead);
            if (B(new Rect(head.xMax - 130 * k, head.y + 10 * k, 116 * k, 32 * k), "Закрыть", sBtn)) Toggle(false);
            // вкладки
            float x = win.x + 12 * k, y = head.yMax + 10 * k;
            foreach (var (key, label) in new[] { ("main", "Главное"), ("vars", "Все переменные"), ("game", "Игра"), ("scan", "Поиск значения"), ("help", "Справка") })
            {
                if (B(new Rect(x, y, 150 * k, 34 * k), label, tab == key ? sBtnOn : sBtn)) { tab = key; scrollY = 0; focusId = null; }
                x += 156 * k;
            }
            if (Btn(new Rect(win.xMax - 160 * k, y, 148 * k, 34 * k), "Обновить", "Найти объекты игры заново — после загрузки сохранения или смены сцены")) Refresh();
            var body = new Rect(win.x + 12 * k, y + 44 * k, w - 24 * k, h - (y + 44 * k - win.y) - 40 * k);
            tip = "";
            if (tab == "main") DrawMain(body);
            else if (tab == "vars") DrawVars(body);
            else if (tab == "game") DrawGame(body);
            else if (tab == "scan") DrawScan(body);
            else DrawHelp(body);
            GUI.Label(new Rect(win.x + 16 * k, win.yMax - 32 * k, w - 32 * k, 26 * k),
                tip != "" ? tip : "Shift+T / F9 — меню   |   Esc — закрыть   |   колесо / PgUp / PgDn — прокрутка   |   игра на паузе", sDim);
            if (repaint) clickPending = false;   // нажатие отработано в этом кадре
        }

        // ---- своё поле ввода
        bool HandleTyping(Event ev)
        {
            switch (ev.keyCode)
            {
                case KeyCode.Return:
                case KeyCode.KeypadEnter:
                    focusCommit?.Invoke(focusBuf);
                    focusId = null;
                    return true;
                case KeyCode.Escape:
                    focusId = null;
                    return true;
                case KeyCode.Backspace:
                    if (focusBuf.Length > 0) focusBuf = focusBuf.Substring(0, focusBuf.Length - 1);
                    if (focusLive) focusCommit?.Invoke(focusBuf);
                    return true;
            }
            char c = ev.character;
            if (c != '\0' && !char.IsControl(c))
            {
                if (focusBuf.Length < 64) focusBuf += c;
                if (focusLive) focusCommit?.Invoke(focusBuf);
                return true;
            }
            return ev.keyCode != KeyCode.None && ev.keyCode != KeyCode.F9;   // остальные клавиши — не в игру
        }

        void Field(Rect r, string id, string text, Action<string> commit, bool live = false, string hint = "")
        {
            bool on = focusId == id;
            if (hint != "" && r.Contains(Event.current.mousePosition)) tip = hint;
            if (B(r, on ? focusBuf + "|" : (string.IsNullOrEmpty(text) ? " " : text), on ? sFieldOn : sField))
            {
                if (!on) { focusId = id; focusBuf = text ?? ""; focusCommit = commit; focusLive = live; }
            }
        }

        bool Btn(Rect r, string text, string hint = "", GUIStyle st = null)
        {
            if (hint != "" && Hover(r)) tip = hint;
            return B(r, text, st ?? sBtn);
        }

        bool Hover(Rect r) => r.Contains(mousePos - groupOrigin) || r.Contains(Event.current.mousePosition);

        // кнопка без GUI.Button: в части игр IMGUI не получает мышь — нажатие из своего опроса
        bool B(Rect r, string text, GUIStyle st)
        {
            bool hov = Hover(r);
            GUI.Box(r, text, hov && hoverOf.TryGetValue(st, out var hs) ? hs : st);
            if (clickPending && Event.current.type == EventType.Repaint && r.Contains(clickPos - groupOrigin))
            {
                clickPending = false;
                return true;
            }
            return false;
        }

        Dictionary<GUIStyle, GUIStyle> hoverOf = new();

        static string Fmt(object v) => v switch
        {
            null => "—",
            float f => f.ToString("0.##"),
            double d => d.ToString("0.##"),
            bool b => b ? "ВКЛ" : "выкл",
            _ => v.ToString()
        };

        // ---- своя прокрутка: группа с обрезкой + смещение, полоса справа (перетаскивается)
        void BeginView(Rect view, float total)
        {
            viewRect = view;
            contentH = total;
            scrollY = Mathf.Clamp(scrollY, 0, Mathf.Max(0, total - view.height));
            var bar = new Rect(view.xMax - 12 * k, view.y, 12 * k, view.height);
            if (total > view.height)
            {
                if (holdMouse && bar.Contains(mousePos))
                    scrollY = Mathf.Clamp((mousePos.y - view.y) / view.height * total - view.height / 2, 0, total - view.height);
                GUI.Box(bar, "", sRow);
                float th = Mathf.Max(30 * k, view.height * view.height / total);
                float ty = view.y + (view.height - th) * (scrollY / (total - view.height));
                GUI.Box(new Rect(bar.x, ty, bar.width, th), "", sThumb);
            }
            GUI.BeginGroup(new Rect(view.x, view.y, view.width - 16 * k, view.height));
            groupOrigin = new Vector2(view.x, view.y);
        }

        bool Visible(float y, float h) => y + h >= scrollY && y <= scrollY + viewRect.height;

        bool onlySure = true;      // «Все переменные»: только поля с понятными (переведёнными) именами

        void DrawVars(Rect body)
        {
            float rh = 40 * k;
            GUI.Label(new Rect(body.x, body.y, 80 * k, 30 * k), "Фильтр", sDim);
            Field(new Rect(body.x + 70 * k, body.y, 300 * k, 30 * k), "filter", filter, t => { filter = t; scrollY = 0; }, true,
                "Щёлкни и печатай: ищет по имени и пути");
            if (Btn(new Rect(body.x + 380 * k, body.y, 220 * k, 30 * k), onlySure ? "Только понятные" : "Все поля",
                    onlySure ? "Скрыты поля с непереведёнными именами (при поиске видно всё). Нажми — показать все"
                             : "Показаны все поля. Нажми — оставить только понятные", onlySure ? sBtnOn : sBtn))
            { onlySure = !onlySure; groupsCache = null; scrollY = 0; }
            float sx = body.xMax - 4 * 60 * k;
            GUI.Label(new Rect(sx - 50 * k, body.y, 50 * k, 30 * k), "шаг", sDim);
            foreach (var s in new[] { 1, 10, 100, 1000 })
            {
                if (B(new Rect(sx, body.y, 56 * k, 30 * k), s.ToString(), step == s ? sBtnOn : sBtn)) step = s;
                sx += 60 * k;
            }
            var q = (filter ?? "").Trim().ToLowerInvariant();
            // группы: объекты со статами (деньги, симпатия…) — сверху по их числу; прочие — свёрнуты.
            // Пересчёт только при смене фильтра/списка: полей бывают десятки тысяч
            if (groupsCache == null || groupsKey != q || groupsVer != entriesVer)
            {
                groupsCache = entries.Where(e => q == "" ? !onlySure || e.Sure : e.Name.ToLowerInvariant().Contains(q) || e.Path.ToLowerInvariant().Contains(q))
                    .GroupBy(e => e.Group).Select(g => (Key: g.Key, Items: g.OrderBy(e => e.Reverted).ThenByDescending(e => e.Stat).ThenByDescending(e => e.Sure).ThenBy(e => e.Name).ToList(), Stats: g.Count(e => e.Stat && !e.Ui)))
                    .OrderByDescending(g => g.Stats).ThenBy(g => g.Key).ToList();
                groupsKey = q;
                groupsVer = entriesVer;
            }
            var main = groupsCache.Where(g => g.Stats > 0 || q != "").ToList();
            var other = groupsCache.Where(g => g.Stats == 0 && q == "").ToList();
            bool openAll = main.Count <= 3 || q != "";
            var autoOpen = new HashSet<string>(main.Take(6).Select(g => g.Key));
            float total = 0;
            foreach (var g in main) total += 34 * k + (openAll || IsOpen(g.Key, autoOpen) ? g.Items.Count * rh : 0);
            total += 40 * k;
            if (showOther) foreach (var g in other) total += 34 * k + (expanded.Contains(g.Key) ? g.Items.Count * rh : 0);
            var view = new Rect(body.x, body.y + 40 * k, body.width, body.height - 40 * k);
            BeginView(view, total);
            float w = view.width - 20 * k, y = 0;
            if (entries.Count == 0)
                GUI.Label(new Rect(0, 0, w, 60 * k), "Объекты игры не найдены. Загрузи сохранение и нажми «Обновить».", sDim);
            foreach (var g in main) y = DrawGroup(g.Key, g.Items, y, w, rh, openAll, autoOpen);
            if (other.Count > 0)
            {
                if (Visible(y, 32 * k) && B(new Rect(0, y - scrollY, 420 * k, 32 * k),
                        (showOther ? "Скрыть" : "Показать") + $" прочие объекты ({other.Count})", sBtn))
                    showOther = !showOther;
                y += 40 * k;
                if (showOther) foreach (var g in other) y = DrawGroup(g.Key, g.Items, y, w, rh, false);
            }
            GUI.EndGroup();
            groupOrigin = Vector2.zero;
        }

        HashSet<string> collapsed = new();

        bool IsOpen(string key, HashSet<string> autoOpen) => expanded.Contains(key) || (autoOpen.Contains(key) && !collapsed.Contains(key));

        float DrawGroup(string key, List<Entry> items, float y, float w, float rh, bool forceOpen, HashSet<string> autoOpen = null)
        {
            autoOpen ??= new HashSet<string>();
            bool isOpen = forceOpen || IsOpen(key, autoOpen);
            if (Visible(y, 30 * k) && B(new Rect(0, y - scrollY, w, 30 * k), (isOpen ? "−  " : "+  ") + key + $"   ({items.Count})", sGroup))
            {
                if (isOpen) { expanded.Remove(key); collapsed.Add(key); }
                else { collapsed.Remove(key); expanded.Add(key); }
            }
            y += 34 * k;
            if (!isOpen) return y;
            foreach (var e in items)
            {
                if (Visible(y, rh)) DrawRow(e, new Rect(0, y - scrollY, w, rh - 4 * k));
                y += rh;
            }
            return y;
        }

        void DrawRow(Entry e, Rect r)
        {
            GUI.Box(r, "", sRow);
            var v = e.Get();
            float ty = r.y + (r.height - 26 * k) / 2;
            // одна строка: имя | значение | кнопки; служебный путь — только в подсказке внизу при наведении
            if (Hover(r)) tip = e.Path + (e.Sure ? "" : "   (имя угадано по названию поля)");
            GUI.Label(new Rect(r.x + 8 * k, ty, 360 * k, 26 * k), e.Name, sText);
            GUI.Label(new Rect(r.x + 380 * k, ty, 150 * k, 26 * k), e.Reverted ? Fmt(v) + "  копия!" : Fmt(v), e.Reverted ? sBad : sAcc);
            if (e.Reverted && Hover(r)) tip = "Копия: игра перезаписывает это значение — ищи оригинал (фильтр по имени или «Поиск значения»)";
            float x = r.x + 540 * k, bh = 30 * k, by = r.y + (r.height - bh) / 2;
            if (e.IsNum)
            {
                double cur = v == null ? 0 : Convert.ToDouble(v);
                if (Btn(new Rect(x, by, 40 * k, bh), "−", "Уменьшить на шаг")) e.Set(cur - step);
                if (Btn(new Rect(x + 44 * k, by, 40 * k, bh), "+", "Увеличить на шаг")) e.Set(cur + step);
                Field(new Rect(x + 90 * k, by, 130 * k, bh), "v:" + e.Path, "",
                    t =>
                    {
                        if (double.TryParse((t ?? "").Replace(',', '.'), System.Globalization.NumberStyles.Float,
                                System.Globalization.CultureInfo.InvariantCulture, out var nv))
                            e.Set(nv);
                    }, false, "Щёлкни, введи число, Enter — поставить");
                bool fz = frozen.ContainsKey(e.Path);
                if (Btn(new Rect(x + 226 * k, by, 130 * k, bh), fz ? "заморожено" : "заморозить",
                        fz ? "Нажми, чтобы снова разрешить игре менять значение" : "Игра не сможет изменить значение", fz ? sBtnOn : sBtn))
                {
                    if (fz) frozen.Remove(e.Path); else frozen[e.Path] = e.Get();
                }
            }
            else if (e.Type == typeof(bool))
            {
                if (Btn(new Rect(x, by, 100 * k, bh), v is true ? "ВКЛ" : "выкл", "Переключить")) e.Set(!(v is true));
            }
            else if (e.Type.IsEnum)
            {
                if (Btn(new Rect(x, by, 160 * k, bh), "следующее", "Перебрать варианты по кругу"))
                {
                    var vals = Enum.GetValues(e.Type);
                    int i = Array.IndexOf(vals, v);
                    e.Set(vals.GetValue((i + 1) % vals.Length));
                }
            }
            else
            {
                Field(new Rect(x, by, 300 * k, bh), "s:" + e.Path, v?.ToString() ?? "", t => e.Set(t), false,
                    "Щёлкни, измени текст, Enter — записать");
            }
            bool fav = Favs().Contains(e.Path);
            if (Btn(new Rect(r.xMax - 128 * k, by, 120 * k, bh), fav ? "убрать" : "в избранное",
                    fav ? "Убрать из «Главного»" : "Показывать на вкладке «Главное»", fav ? sBtnOn : sBtn))
                ToggleFav(e.Path);
        }

        // ---------------------------------------------------------- избранное
        string FavFile => Path.Combine(Plugin.Dir, "favorites.json");

        HashSet<string> Favs()
        {
            if (favs != null) return favs;
            favs = new HashSet<string>();
            try
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(FavFile));
                if (doc.RootElement.TryGetProperty(Application.productName, out var arr))
                    foreach (var x in arr.EnumerateArray()) favs.Add(x.GetString());
            }
            catch { }
            return favs;
        }

        void ToggleFav(string path)
        {
            if (!Favs().Remove(path)) favs.Add(path);
            try
            {
                var all = new Dictionary<string, List<string>>();
                try
                {
                    using var doc = JsonDocument.Parse(File.ReadAllText(FavFile));
                    foreach (var pr in doc.RootElement.EnumerateObject())
                        all[pr.Name] = pr.Value.EnumerateArray().Select(x => x.GetString()).ToList();
                }
                catch { }
                all[Application.productName] = favs.OrderBy(x => x).ToList();
                File.WriteAllText(FavFile, JsonSerializer.Serialize(all, new JsonSerializerOptions { WriteIndented = true }));
            }
            catch (Exception ex) { Plugin.L.LogWarning("favorites: " + ex.Message); }
        }

        int mainVer = -1, mainFavs = -1;
        List<Entry> mFav = new(), mFungus = new();
        (string Key, List<Entry> Stats) mBest;
        List<(string Key, int Count)> mLists = new();

        void BuildMain()
        {
            mainVer = entriesVer;
            mainFavs = Favs().Count;
            mFav = entries.Where(e => Favs().Contains(e.Path)).ToList();
            // главный объект: группа экземпляра (не static, не интерфейс) с наибольшим числом статов
            mBest = entries.Where(e => e.Owner != null && !e.Ui && !e.Group.Contains("(static)") && !e.Group.Contains("["))
                .GroupBy(e => e.Group).Select(g => (g.Key, Stats: g.Where(e => e.Stat).ToList()))
                .Where(g => g.Stats.Count > 0).OrderByDescending(g => g.Stats.Count).FirstOrDefault();
            mFungus = entries.Where(e => e.Group.StartsWith("Переменные сценария")).ToList();
            // списки (флаги, предметы…): группы вида «…​.flags», элементы которых подписаны
            // только списки внутри главного объекта (иначе всплывают служебные списки диалогов и т.п.)
            mLists = entries.Where(e => e.Path.Contains("[") && mBest.Key != null && e.Group.StartsWith(mBest.Key + ".")).GroupBy(e => e.Group)
                .Select(g => (g.Key, Count: g.Select(e => e.Path.Substring(0, e.Path.IndexOf(']') + 1)).Distinct().Count()))
                .OrderByDescending(g => g.Count).Take(6).ToList();

        }

        // ---------------------------------------------------------- вкладка «Главное»
        // Время (если игра умеет) + разделы-гармошки: избранное, главное состояние (сначала только
        // понятные статы), переменные сценария, списки. Открыты по умолчанию только первые два.
        HashSet<string> mainOpen = new() { "fav", "best" };
        bool bestAll;
        float mainTotal = 1000;
        int pendingSkip, pendingStamina;
        string skipMsg = "";

        void DrawMain(Rect body)
        {
            float rh = 40 * k;
            float sx = body.xMax - 4 * 60 * k;
            GUI.Label(new Rect(body.x, body.y, 600 * k, 30 * k), "Самое нужное. Остальное — во «Все переменные».", sDim);
            GUI.Label(new Rect(sx - 50 * k, body.y, 50 * k, 30 * k), "шаг", sDim);
            foreach (var st in new[] { 1, 10, 100, 1000 })
            {
                if (Btn(new Rect(sx, body.y, 56 * k, 30 * k), st.ToString(), "На сколько меняют «−» / «+»", step == st ? sBtnOn : sBtn)) step = st;
                sx += 60 * k;
            }
            if (mainVer != entriesVer || mainFavs != Favs().Count) BuildMain();
            var view = new Rect(body.x, body.y + 40 * k, body.width, body.height - 40 * k);
            BeginView(view, mainTotal);
            float w = view.width - 20 * k, y = 0;

            // заголовок раздела — кнопка «свернуть/развернуть»
            bool Section(string id, string text)
            {
                bool isOpen = mainOpen.Contains(id);
                if (Visible(y, 32 * k) && B(new Rect(0, y - scrollY, w, 32 * k), (isOpen ? "−  " : "+  ") + text, sGroup))
                {
                    if (isOpen) mainOpen.Remove(id); else mainOpen.Add(id);
                    isOpen = !isOpen;
                }
                y += 38 * k;
                return isOpen;
            }
            void Rows(IEnumerable<Entry> es)
            {
                foreach (var e in es)
                {
                    if (Visible(y, rh)) DrawRow(e, new Rect(0, y - scrollY, w, rh - 4 * k));
                    y += rh;
                }
            }
            void Note(string text)
            {
                if (Visible(y, 30 * k)) GUI.Label(new Rect(8 * k, y - scrollY, w, 30 * k), text, sDim);
                y += 34 * k;
            }

            if (GameTime.Supported) y = DrawTime(w, y);

            if (Section("fav", $"Избранное ({mFav.Count})"))
            {
                if (mFav.Count == 0) Note("Пусто. Жми «в избранное» у нужных строк — они будут здесь всегда.");
                Rows(mFav);
            }
            y += 6 * k;
            if (mBest.Key != null)
            {
                var sure = mBest.Stats.Where(e => e.Sure).OrderBy(e => e.Name).ToList();
                var shown = bestAll || sure.Count == 0 ? mBest.Stats.OrderByDescending(e => e.Sure).ThenBy(e => e.Name).ToList() : sure;
                if (Section("best", $"Главное: {mBest.Stats[0].OwnerType}   ({mBest.Stats.Count})"))
                {
                    Rows(shown);
                    float bx = 0;
                    if (shown.Count < mBest.Stats.Count || bestAll)
                    {
                        if (Visible(y, 32 * k) && Btn(new Rect(bx, y - scrollY, 300 * k, 32 * k),
                                bestAll ? "Только понятные" : $"Показать ещё {mBest.Stats.Count - shown.Count}",
                                "Остальные — с непереведёнными именами полей"))
                            bestAll = !bestAll;
                        bx += 310 * k;
                    }
                    if (Visible(y, 32 * k) && B(new Rect(bx, y - scrollY, 300 * k, 32 * k), "Все поля этого объекта", sBtn))
                    {
                        tab = "vars";
                        filter = mBest.Key;
                        scrollY = 0;
                    }
                    y += 42 * k;
                }
            }
            else
            {
                Section("best", "Главное состояние не найдено");
                Note("Загрузи сохранение и нажми «Обновить» — в главном меню игра ещё пустая.");
            }
            if (mFungus.Count > 0 && Section("fungus", $"Переменные сценария ({mFungus.Count})"))
                Rows(mFungus.OrderByDescending(e => e.Stat).ThenBy(e => e.Name).Take(30));
            if (mLists.Count > 0 && Section("lists", $"Списки: флаги, предметы… ({mLists.Count})"))
            {
                foreach (var (key, cnt) in mLists)
                {
                    if (Visible(y, 34 * k) && Btn(new Rect(20 * k, y - scrollY, 640 * k, 34 * k), $"{key}   ({cnt} шт.)", "Открыть во «Все переменные»"))
                    {
                        tab = "vars";
                        filter = key;
                        scrollY = 0;
                    }
                    y += 40 * k;
                }
            }
            GUI.EndGroup();
            groupOrigin = Vector2.zero;
            mainTotal = y + 10 * k;
        }

        // блок «Время»: текущий день и пропуск (выполняется после закрытия меню)
        float DrawTime(float w, float y)
        {
            int now = GameTime.Now();
            if (Visible(y, 36 * k))
                GUI.Label(new Rect(0, y - scrollY, w, 32 * k), "Время:  " + (now >= 0 ? GameTime.Describe(now) : "—"), sAcc);
            y += 38 * k;
            var why = GameTime.Blocked();
            if (now < 0)
            {
                if (Visible(y, 28 * k)) GUI.Label(new Rect(0, y - scrollY, w, 28 * k), why, sDim);
                return y + 38 * k;
            }
            float x = 0;
            void Skip(string label, int minutes, int stamina, string hint)
            {
                if (Visible(y, 36 * k) && Btn(new Rect(x, y - scrollY, 250 * k, 34 * k), label, hint))
                {
                    if (why != "") skipMsg = why;
                    else if (minutes > 0) { pendingSkip = minutes; pendingStamina = stamina; skipMsg = ""; Toggle(false); }
                }
                x += 258 * k;
            }
            int toMorning = GameTime.MinutesToMorning(now, 8);
            Skip("Пропустить день (до 8:00)", toMorning, GameTime.Recovery,
                $"Перемотать {toMorning / 60} ч {toMorning % 60} мин до утра; силы восстанавливаются как во сне, голод растёт");
            Skip("+1 час", 60, GameTime.Normal, "Перемотать час");
            Skip("+6 часов", 360, GameTime.Normal, "Перемотать 6 часов");
            y += 40 * k;
            if (why != "" || skipMsg != "")
            {
                if (Visible(y, 28 * k)) GUI.Label(new Rect(0, y - scrollY, w, 28 * k), skipMsg != "" ? skipMsg : why, skipMsg != "" ? sBad : sDim);
                y += 30 * k;
            }
            return y + 8 * k;
        }

        void DrawScan(Rect body)
        {
            GUI.Label(new Rect(body.x, body.y, body.width, 26 * k), "Как ArtMoney, но по именам: «Снимок» → закрой меню, поиграй (потрать деньги, подними стат) → сужай.", sDim);
            float x = body.x, y = body.y + 32 * k;
            if (B(new Rect(x, y, 130 * k, 32 * k), "Снимок", sBtn))
            {
                Refresh();
                snap = Numbers();
                cands = snap.Keys.ToList();
                scanMsg = $"Снимок: {cands.Count} чисел. Поиграй и сужай.";
            }
            x += 136 * k;
            foreach (var (label, mode) in new[] { ("изменились", 0), ("не изменились", 1), ("больше", 2), ("меньше", 3) })
            {
                if (B(new Rect(x, y, 150 * k, 32 * k), label, sBtn)) Narrow(mode);
                x += 156 * k;
            }
            GUI.Label(new Rect(body.x, y + 40 * k, body.width, 28 * k), scanMsg, sAcc);
            if (cands.Count == 0 || cands.Count > 80) return;
            var byPath = new Dictionary<string, Entry>();
            foreach (var en in entries) if (!byPath.ContainsKey(en.Path)) byPath[en.Path] = en;
            var view = new Rect(body.x, y + 76 * k, body.width, body.height - 116 * k);
            BeginView(view, cands.Count * 44 * k);
            float yy = 0;
            foreach (var p in cands)
                if (byPath.TryGetValue(p, out var e))
                {
                    if (Visible(yy, 40 * k)) DrawRow(e, new Rect(0, yy - scrollY, view.width - 24 * k, 40 * k));
                    yy += 44 * k;
                }
            GUI.EndGroup();
            groupOrigin = Vector2.zero;
        }

        Dictionary<string, double> Numbers()
        {
            var d = new Dictionary<string, double>();
            foreach (var e in entries)
                if (e.IsNum) { var v = e.Get(); if (v != null) d[e.Path] = Convert.ToDouble(v); }
            return d;
        }

        void Narrow(int mode)
        {
            if (snap.Count == 0) { scanMsg = "Сначала «Снимок»."; return; }
            Refresh();
            var now = Numbers();
            cands = cands.Where(p => now.ContainsKey(p) && snap.ContainsKey(p) && (mode == 0 ? now[p] != snap[p] : mode == 1 ? now[p] == snap[p]
                : mode == 2 ? now[p] > snap[p] : now[p] < snap[p])).ToList();
            snap = now;
            scanMsg = $"Осталось: {cands.Count}" + (cands.Count > 80 ? " (покажу, когда будет ≤ 80)" : "");
        }

        // ---------------------------------------------------------- профиль игры
        // Темп и заморозки, которые ставятся сами при каждом запуске (profiles.json, по productName).
        string ProfFile => Path.Combine(Plugin.Dir, "profiles.json");
        bool profileLoaded;

        Dictionary<string, JsonElement> ReadProfiles()
        {
            var all = new Dictionary<string, JsonElement>();
            try
            {
                using var doc = JsonDocument.Parse(File.ReadAllText(ProfFile));
                foreach (var pr in doc.RootElement.EnumerateObject()) all[pr.Name] = pr.Value.Clone();
            }
            catch { }
            return all;
        }

        int hasProf = -1;                                   // кэш: есть ли профиль (файл не читаем каждый кадр)
        bool HasProfile()
        {
            if (hasProf < 0) hasProf = ReadProfiles().ContainsKey(Application.productName) ? 1 : 0;
            return hasProf == 1;
        }

        void SaveProfile(bool on)
        {
            var all = new Dictionary<string, object>();
            foreach (var kv in ReadProfiles()) all[kv.Key] = kv.Value;
            if (on) all[Application.productName] = new Dictionary<string, object> { ["speed"] = speed, ["frozen"] = frozen };
            else all.Remove(Application.productName);
            hasProf = on ? 1 : 0;
            try { File.WriteAllText(ProfFile, JsonSerializer.Serialize(all, new JsonSerializerOptions { WriteIndented = true })); }
            catch (Exception ex) { Plugin.L.LogWarning("profiles: " + ex.Message); }
        }

        // сначала темп; заморозки — когда объекты игры появятся (после загрузки сохранения):
        // поиск через 10 с, потом раз в минуту, до 10 минут
        void ProfileTick()
        {
            if (!profileLoaded)
            {
                profileLoaded = true;
                if (!ReadProfiles().TryGetValue(Application.productName, out var p)) return;
                if (p.TryGetProperty("speed", out var sp) && sp.TryGetSingle(out var s) && !Mathf.Approximately(s, 1f)) { speed = s; prevScale = s; Time.timeScale = s; }
                if (p.TryGetProperty("frozen", out var fr) && fr.ValueKind == JsonValueKind.Object)
                {
                    pendingProfile = new Dictionary<string, JsonElement>();
                    foreach (var kv in fr.EnumerateObject()) pendingProfile[kv.Name] = kv.Value;
                }
            }
            if (pendingProfile == null || pendingProfile.Count == 0 || open || Time.realtimeSinceStartup < profileNext) return;
            profileNext = Time.realtimeSinceStartup + 60f;
            if (Time.realtimeSinceStartup > profileUntil) { pendingProfile = null; return; }
            try
            {
                Refresh();
                foreach (var e in entries)
                {
                    if (!pendingProfile.TryGetValue(e.Path, out var j)) continue;
                    var cur = e.Get();
                    if (cur == null) continue;
                    object v = j.ValueKind switch
                    {
                        JsonValueKind.True => true,
                        JsonValueKind.False => false,
                        JsonValueKind.String => j.GetString(),
                        _ => j.GetDouble()
                    };
                    frozen[e.Path] = Convert.ChangeType(v, cur.GetType());
                    pendingProfile.Remove(e.Path);
                }
                Release();
            }
            catch (Exception ex) { Plugin.L.LogWarning("profile: " + ex.Message); }
        }

        // ---------------------------------------------------------- вкладка «Игра»: темп и телепорт
        static GameObject Player()
        {
            try { var go = GameObject.FindWithTag("Player"); if (go != null) return go; } catch { }   // тега может не быть
            foreach (var n in new[] { "Player", "player", "Hero", "PlayerCharacter", "FPSController", "ThirdPersonController" })
                try { var go = GameObject.Find(n); if (go != null) return go; } catch { }
            return null;
        }

        // физика держит своё положение тела: без синхронизации CharacterController вернёт игрока назад
        static void SyncPhysics()
        {
            foreach (var t in new[] { "UnityEngine.Physics, UnityEngine.PhysicsModule", "UnityEngine.Physics2D, UnityEngine.Physics2DModule" })
                try { Type.GetType(t)?.GetMethod("SyncTransforms", Type.EmptyTypes)?.Invoke(null, null); } catch { }
        }

        static string V3(Vector3 v) => $"({v.x:0.#}, {v.y:0.#}, {v.z:0.#})";

        void DrawGame(Rect body)
        {
            float x = body.x, y = body.y;
            GUI.Label(new Rect(x, y, body.width, 28 * k), "Скорость игры", sAcc);
            y += 34 * k;
            foreach (var (val, label) in new[] { (0f, "пауза"), (0.25f, "×0.25"), (0.5f, "×0.5"), (1f, "×1"), (2f, "×2"), (3f, "×3"), (5f, "×5") })
            {
                if (B(new Rect(x, y, 100 * k, 32 * k), label, Mathf.Approximately(speed, val) ? sBtnOn : sBtn)) { speed = val; prevScale = val; }
                x += 106 * k;
            }
            y += 40 * k;
            GUI.Label(new Rect(body.x, y, body.width, 26 * k), "Темп включится после закрытия меню (пока меню открыто, игра на паузе); пока он не ×1, в углу виден значок.", sDim);
            y += 40 * k;
            GUI.Label(new Rect(body.x, y, body.width, 28 * k), "Профиль игры", sAcc);
            y += 34 * k;
            bool hasPr = HasProfile();
            if (Btn(new Rect(body.x, y, 240 * k, 32 * k), "Сохранить профиль", "Темп и заморозки будут ставиться сами при каждом запуске игры")) SaveProfile(true);
            if (hasPr && B(new Rect(body.x + 248 * k, y, 220 * k, 32 * k), "Удалить профиль", sBtn)) SaveProfile(false);
            GUI.Label(new Rect(body.x + 480 * k, y, body.width - 480 * k, 32 * k), hasPr ? "профиль есть: ставится сам при запуске" : "профиля нет", sDim);
            y += 44 * k;
            GUI.Label(new Rect(body.x, y, body.width, 28 * k), "Игрок и точки телепорта", sAcc);
            y += 34 * k;
            var p = Player();
            if (p == null)
            {
                GUI.Label(new Rect(body.x, y, body.width, 26 * k), "Игрок не найден: нет объекта с тегом Player или с именем Player / Hero.", sDim);
                return;
            }
            var pos = p.transform.position;
            GUI.Label(new Rect(body.x, y, body.width * 0.6f, 30 * k), p.name + ": " + V3(pos), sText);
            if (Btn(new Rect(body.x + body.width * 0.6f, y, 220 * k, 32 * k), "Запомнить место", "Точки живут до выхода из игры"))
                places.Add((UnityEngine.SceneManagement.SceneManager.GetActiveScene().name + "  " + V3(pos), pos));
            y += 44 * k;
            for (int i = 0; i < places.Count; i++)
            {
                var (name, at) = places[i];
                GUI.Label(new Rect(body.x, y, body.width * 0.6f, 30 * k), name, sText);
                if (B(new Rect(body.x + body.width * 0.6f, y, 110 * k, 32 * k), "сюда", sBtn))
                {
                    p.transform.position = at;
                    SyncPhysics();
                    Toggle(false);
                    return;
                }
                if (B(new Rect(body.x + body.width * 0.6f + 116 * k, y, 50 * k, 32 * k), "×", sBtn)) { places.RemoveAt(i); return; }
                y += 38 * k;
            }
        }

        void DrawHelp(Rect body)
        {
            string[] lines =
            {
                "Открыть и закрыть: Shift+T или F9, Esc — закрыть. Пока меню открыто, игра на паузе.",
                "",
                "Главное: время и пропуск дня, избранное, главные статы игры. Разделы сворачиваются щелчком",
                "по заголовку. «в избранное» у любой строки — она всегда будет наверху (запоминается).",
                "Пропуск дня — только в комнате; меню закроется, время перемотает сама игра. Сохранись перед пропуском.",
                "",
                "Все переменные: всё найденное. По умолчанию — только поля с понятными именами (кнопка «Все поля»).",
                "Фильтр — щёлкни по полю и печатай. «−» / «+» с шагом, поле — своё число и Enter,",
                "«заморозить» — игра не сможет изменить значение. Наведи на строку — внизу видно, где оно лежит.",
                "Красное «копия!» — игра перезаписала значение: это экранная копия, ищи оригинал.",
                "",
                "Игра: скорость (пауза, ×0.25 … ×5) и точки телепорта игрока (объект с тегом Player).",
                "",
                "Поиск значения: «Снимок», закрой меню, измени значение в игре, вернись и жми",
                "«изменились» / «больше» / «меньше», пока не останется пара строк.",
                "",
                "«Обновить» — после загрузки сохранения или смены сцены.",
                "Сохраняется игра сама — перед экспериментами сохранись. F7 — UnityExplorer (полный просмотр объектов).",
            };
            float y = body.y;
            foreach (var l in lines) { GUI.Label(new Rect(body.x, y, body.width, 26 * k), l, sText); y += 26 * k; }
        }
    }
}
