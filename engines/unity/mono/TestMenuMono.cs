// TestMenuMoon для Unity-игр на Mono (BepInEx 5). Shift+T / F9 — меню, F7 — UnityExplorer.
//
// Исходник собирается при установке (engines/unity/inject.py) системным csc.exe прямо против
// библиотек игры (<игра>_Data/Managed) — поэтому язык C# 5 (без $"", ?., кортежей) и только API
// .NET 3.5: так плагин подходит к любой версии Unity и рантайму игры.
//
// Что умеет: поля объектов игры (компоненты сцены, ScriptableObject, статика) с понятными
// именами, правка −/+ и вводом, заморозка, «Главное» — поля-статы, поиск «снимок → сужение»,
// скорость игры с паузой, профиль игры (темп и заморозки при запуске), телепорт игрока.
// Пока меню открыто, игра на паузе (Time.timeScale = 0), курсор освобождён.
using System;
using System.Collections;
using System.Collections.Generic;
using System.IO;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;
using BepInEx;
using UnityEngine;

namespace TestMenuMono
{
    [BepInPlugin("testmenumoon.mono", "TestMenu", "1.0.0")]
    public class Plugin : BaseUnityPlugin
    {
        internal static string Dir;
        internal static Plugin I;

        void Awake()
        {
            I = this;
            Dir = Path.GetDirectoryName(Info.Location);
            Words.Load(Path.Combine(Dir, "tm_words.json"));
            Profile.Load();
        }

        void Update() { Menu.Update(); }
        void OnGUI() { Menu.OnGUI(); }
        internal static void Log(string s) { if (I != null) I.Logger.LogInfo(s); }
    }

    // ------------------------------------------------------------ слова: имя поля -> по-русски
    internal static class Words
    {
        internal static Dictionary<string, string> Map = new Dictionary<string, string>();
        internal static HashSet<string> Stat = new HashSet<string>();

        internal static void Load(string path)
        {
            try
            {
                string t = File.ReadAllText(path, Encoding.UTF8);
                int sw = t.IndexOf("\"stat_words\"");
                string head = sw > 0 ? t.Substring(0, sw) : t;
                foreach (Match m in Regex.Matches(head, "\"([A-Za-z_]+)\"\\s*:\\s*\"([^\"]*)\""))
                    Map[m.Groups[1].Value.ToLowerInvariant()] = m.Groups[2].Value;
                if (sw > 0)
                {
                    int a = t.IndexOf('[', sw), b = t.IndexOf(']', a);
                    foreach (Match m in Regex.Matches(t.Substring(a, b - a), "\"([^\"]+)\""))
                        Stat.Add(m.Groups[1].Value.ToLowerInvariant());
                }
            }
            catch (Exception e) { Plugin.Log("tm_words.json: " + e.Message); }
        }

        internal static List<string> Tokens(string name)
        {
            var res = new List<string>();
            string s = Regex.Replace(name, "<(\\w+)>k__BackingField", "$1");
            s = Regex.Replace(s, "([a-z0-9])([A-Z])", "$1 $2");
            foreach (string p in Regex.Split(s, "[^A-Za-z0-9]+"))
                if (p.Length > 0 && !Regex.IsMatch(p, "^m$|^\\d+$")) res.Add(p.ToLowerInvariant());
            return res;
        }

        internal static bool IsStat(string field)
        {
            foreach (string t in Tokens(field))
                if (Stat.Contains(t) || Map.ContainsKey(t)) return true;
            return false;
        }

        internal static string Nice(string field)
        {
            var parts = new List<string>();
            bool any = false;
            foreach (string t in Tokens(field))
            {
                string w;
                if (Map.TryGetValue(t, out w)) { parts.Add(w); any = true; }
                else parts.Add(t);
            }
            if (parts.Count == 0) return field;
            string r = string.Join(" ", parts.ToArray());
            r = char.ToUpper(r[0]) + r.Substring(1);
            return any ? r : field;
        }
    }

    // ------------------------------------------------------------ одно значение игры
    internal class Entry
    {
        internal string Group, Path, Label;
        internal Type Type;
        internal object Owner;          // объект (null — статическое поле)
        internal FieldInfo Field;
        internal bool Stat;

        internal object Get()
        {
            try { return Field.GetValue(Owner); } catch { return null; }
        }

        internal void Set(object v)
        {
            try
            {
                if (Type.IsEnum) v = Enum.ToObject(Type, v);
                else v = Convert.ChangeType(v, Type);
                Field.SetValue(Owner, v);
            }
            catch (Exception e) { Plugin.Log("set " + Path + ": " + e.Message); }
        }

        internal bool IsNum { get { return Type == typeof(int) || Type == typeof(float) || Type == typeof(double) || Type == typeof(long) || Type == typeof(short) || Type == typeof(byte) || Type == typeof(uint); } }
    }

    // ------------------------------------------------------------ сбор полей
    internal static class Scanner
    {
        const BindingFlags F = BindingFlags.Instance | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly;
        const BindingFlags S = BindingFlags.Static | BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.DeclaredOnly;

        static bool IsGameAsm(Assembly a)
        {
            string n = a.GetName().Name;
            if (n.StartsWith("Assembly-CSharp")) return true;
            string[] skip = { "mscorlib", "System", "Mono", "Unity", "UnityEngine", "BepInEx", "0Harmony", "Harmony", "MonoMod",
                "netstandard", "TestMenu", "UnityExplorer", "UniverseLib", "Newtonsoft", "DOTween", "Rewired", "Steamworks",
                "Facepunch", "TextMeshPro", "Cinemachine", "Sirenix", "FMOD", "Photon", "Mirror", "I18N", "Microsoft" };
            foreach (string s in skip) if (n.StartsWith(s)) return false;
            return true;
        }

        static bool Scalar(Type t)
        {
            return t.IsPrimitive && t != typeof(IntPtr) && t != typeof(UIntPtr) && t != typeof(char) || t == typeof(string) || t.IsEnum;
        }

        internal static List<Type> GameTypes()
        {
            var res = new List<Type>();
            foreach (Assembly a in AppDomain.CurrentDomain.GetAssemblies())
            {
                if (!IsGameAsm(a)) continue;
                Type[] ts;
                try { ts = a.GetTypes(); }
                catch (ReflectionTypeLoadException e) { ts = e.Types; }
                catch { continue; }
                foreach (Type t in ts) if (t != null) res.Add(t);
            }
            return res;
        }

        static void Fields(object owner, Type t, string group, string path, int depth, List<Entry> outList, HashSet<object> seen)
        {
            if (outList.Count > 6000) return;
            for (Type cur = t; cur != null && cur != typeof(object) && cur != typeof(MonoBehaviour) && cur != typeof(ScriptableObject)
                 && cur != typeof(Component) && cur != typeof(UnityEngine.Object); cur = cur.BaseType)
            {
                foreach (FieldInfo f in cur.GetFields(F))
                {
                    if (f.IsLiteral || f.Name.Contains("<>") || f.FieldType.IsPointer) continue;
                    string name = Regex.Replace(f.Name, "<(\\w+)>k__BackingField", "$1");
                    if (Scalar(f.FieldType))
                    {
                        if (f.IsInitOnly) continue;
                        var e = new Entry();
                        e.Group = group; e.Path = path + "." + name; e.Type = f.FieldType; e.Owner = owner; e.Field = f;
                        e.Stat = Words.IsStat(name) && f.FieldType != typeof(string);
                        e.Label = Words.Nice(name);
                        outList.Add(e);
                    }
                    else if (depth > 0 && !f.FieldType.IsValueType && !typeof(UnityEngine.Object).IsAssignableFrom(f.FieldType)
                             && !typeof(IEnumerable).IsAssignableFrom(f.FieldType) && !typeof(Delegate).IsAssignableFrom(f.FieldType)
                             && f.FieldType.Assembly != typeof(object).Assembly)
                    {
                        object v = null;
                        try { v = f.GetValue(owner); } catch { }
                        if (v == null || seen.Contains(v)) continue;
                        seen.Add(v);
                        Fields(v, v.GetType(), group, path + "." + name, depth - 1, outList, seen);
                    }
                }
            }
        }

        internal static List<Entry> Collect()
        {
            var res = new List<Entry>();
            var seen = new HashSet<object>();
            var types = GameTypes();
            var gameSet = new HashSet<Type>(types);
            // компоненты сцены и ScriptableObject игры; типы с толпой экземпляров (пули, клетки) — мимо
            var counts = new Dictionary<Type, int>();
            var objs = new List<UnityEngine.Object>();
            foreach (UnityEngine.Object o in UnityEngine.Object.FindObjectsOfType(typeof(MonoBehaviour))) objs.Add(o);
            foreach (UnityEngine.Object o in Resources.FindObjectsOfTypeAll(typeof(ScriptableObject))) objs.Add(o);
            foreach (UnityEngine.Object o in objs)
            {
                if (o == null || !gameSet.Contains(o.GetType())) continue;
                int c; counts.TryGetValue(o.GetType(), out c); counts[o.GetType()] = c + 1;
            }
            foreach (UnityEngine.Object o in objs)
            {
                if (o == null || !gameSet.Contains(o.GetType()) || counts[o.GetType()] > 25 || seen.Contains(o)) continue;
                seen.Add(o);
                string g = o.GetType().Name + (o is ScriptableObject ? " (данные)" : "") + (counts[o.GetType()] > 1 ? " [" + o.name + "]" : "");
                Fields(o, o.GetType(), g, g, 2, res, seen);
            }
            // статика: синглтоны и глобальные счётчики
            foreach (Type t in types)
            {
                if (t.IsGenericTypeDefinition || t.Name.StartsWith("<")) continue;
                FieldInfo[] fs;
                try { fs = t.GetFields(S); } catch { continue; }
                foreach (FieldInfo f in fs)
                {
                    if (f.IsLiteral || f.Name.Contains("<>")) continue;
                    try
                    {
                        if (Scalar(f.FieldType) && !f.IsInitOnly && !Regex.IsMatch(f.Name, "^[A-Z0-9_]+$"))
                        {
                            var e = new Entry();
                            e.Group = t.Name + " (статика)"; e.Path = t.Name + "." + f.Name; e.Type = f.FieldType; e.Field = f;
                            e.Stat = Words.IsStat(f.Name) && f.FieldType != typeof(string);
                            e.Label = Words.Nice(f.Name);
                            res.Add(e);
                        }
                        else if (gameSet.Contains(f.FieldType) && !typeof(UnityEngine.Object).IsAssignableFrom(f.FieldType))
                        {
                            object v = f.GetValue(null);
                            if (v != null && !seen.Contains(v))
                            {
                                seen.Add(v);
                                Fields(v, v.GetType(), t.Name + "." + f.Name, t.Name + "." + f.Name, 2, res, seen);
                            }
                        }
                    }
                    catch { }
                }
            }
            return res;
        }
    }

    // ------------------------------------------------------------ профиль игры (profiles.txt)
    // строка: <productName> \t speed=<k> \t <путь>=<значение> …
    internal static class Profile
    {
        internal static float Speed = 1f;
        internal static Dictionary<string, string> Frozen = new Dictionary<string, string>();
        internal static bool Has;
        static string FileName { get { return Path.Combine(Plugin.Dir, "profiles.txt"); } }

        internal static void Load()
        {
            try
            {
                if (!File.Exists(FileName)) return;
                foreach (string line in File.ReadAllLines(FileName, Encoding.UTF8))
                {
                    string[] p = line.Split('\t');
                    if (p.Length == 0 || p[0] != Application.productName) continue;
                    Has = true;
                    for (int i = 1; i < p.Length; i++)
                    {
                        int eq = p[i].IndexOf('=');
                        if (eq <= 0) continue;
                        string k = p[i].Substring(0, eq), v = p[i].Substring(eq + 1);
                        if (k == "speed") float.TryParse(v, System.Globalization.NumberStyles.Float, System.Globalization.CultureInfo.InvariantCulture, out Speed);
                        else Frozen[k] = v;
                    }
                }
            }
            catch (Exception e) { Plugin.Log("profiles: " + e.Message); }
        }

        internal static void Save(bool on, float speed, Dictionary<string, object> frozen)
        {
            var lines = new List<string>();
            try
            {
                if (File.Exists(FileName))
                    foreach (string l in File.ReadAllLines(FileName, Encoding.UTF8))
                        if (!l.StartsWith(Application.productName + "\t")) lines.Add(l);
            }
            catch { }
            if (on)
            {
                var sb = new StringBuilder(Application.productName);
                sb.Append("\tspeed=").Append(speed.ToString(System.Globalization.CultureInfo.InvariantCulture));
                foreach (var kv in frozen)
                    sb.Append('\t').Append(kv.Key).Append('=').Append(Convert.ToString(kv.Value, System.Globalization.CultureInfo.InvariantCulture).Replace("\t", " "));
                lines.Add(sb.ToString());
            }
            Has = on;
            try { File.WriteAllText(FileName, string.Join("\n", lines.ToArray()) + "\n", Encoding.UTF8); }
            catch (Exception e) { Plugin.Log("profiles: " + e.Message); }
        }
    }

    // ------------------------------------------------------------ меню
    internal static class Menu
    {
        static bool open;
        static float prevScale = 1f, speed = 1f;
        static int stepState;      // шаг кадра: 1 — запрошен, 2 — идёт кадр
        static bool showFps;       // счётчик FPS в углу экрана
        static float fps;          // сглаженный FPS (по реальному времени)
        static CursorLockMode prevLock;
        static bool prevVisible;
        static string tab = "main", filter = "", tip = "";
        static int step = 1;
        static List<Entry> entries = new List<Entry>();
        static Dictionary<string, object> frozen = new Dictionary<string, object>();
        static Dictionary<string, double> snap = new Dictionary<string, double>();
        static List<string> cands = new List<string>();
        static string scanMsg = "Нажми «Снимок», закрой меню, поиграй и возвращайся сужать.";
        static Vector2 scroll;
        static Dictionary<string, string> edit = new Dictionary<string, string>();
        static HashSet<string> openGroups = new HashSet<string>();
        static float profileAt = 10f, profileUntil = 600f;
        static bool profileSpeedDone;
        static List<KeyValuePair<string, Vector3>> places = new List<KeyValuePair<string, Vector3>>();
        static GUIStyle sHead, sDim, sAcc, sBox;

        internal static void Update()
        {
            ProfileTick();
            float udt = Time.unscaledDeltaTime;
            if (udt > 0f) fps = fps <= 0f ? 1f / udt : Mathf.Lerp(fps, 1f / udt, 0.1f);
            // шаг кадра на паузе: один кадр с темпом 1, затем снова пауза
            if (stepState == 1) { Time.timeScale = 1f; stepState = 2; }
            else if (stepState == 2) { Time.timeScale = open ? 0f : speed; stepState = 0; }
            if (stepState == 0 && !open && speed != 1f && Mathf.Approximately(Time.timeScale, 1f)) Time.timeScale = speed;
            if (frozen.Count == 0) return;
            foreach (Entry e in entries)
            {
                object v;
                if (frozen.TryGetValue(e.Path, out v) && !Equals(e.Get(), v)) e.Set(v);
            }
        }

        static void ProfileTick()
        {
            if (!profileSpeedDone)
            {
                profileSpeedDone = true;
                if (Profile.Has && Profile.Speed != 1f) { speed = Profile.Speed; prevScale = speed; Time.timeScale = speed; }
            }
            if (Profile.Frozen.Count == 0 || open || Time.realtimeSinceStartup < profileAt) return;
            profileAt = Time.realtimeSinceStartup + 60f;
            if (Time.realtimeSinceStartup > profileUntil) { Profile.Frozen.Clear(); return; }
            try
            {
                Refresh();
                foreach (Entry e in entries)
                {
                    string v;
                    if (!Profile.Frozen.TryGetValue(e.Path, out v)) continue;
                    object val = e.Type.IsEnum ? Enum.Parse(e.Type, v) : Convert.ChangeType(v, e.Type, System.Globalization.CultureInfo.InvariantCulture);
                    frozen[e.Path] = val;
                    Profile.Frozen.Remove(e.Path);
                }
                Release();
            }
            catch (Exception ex) { Plugin.Log("profile: " + ex.Message); }
        }

        static void Refresh() { entries = Scanner.Collect(); }

        // меню закрыто: держим только замороженные строки (сцены выгружаются)
        static void Release()
        {
            var keep = new List<Entry>();
            foreach (Entry e in entries) if (frozen.ContainsKey(e.Path)) keep.Add(e);
            entries = keep;
        }

        static void Toggle(bool on)
        {
            if (on == open) return;
            open = on;
            if (on)
            {
                prevScale = Time.timeScale;
                Time.timeScale = 0f;
                prevLock = Cursor.lockState;
                prevVisible = Cursor.visible;
                Cursor.lockState = CursorLockMode.None;
                Cursor.visible = true;
                Refresh();
            }
            else
            {
                Time.timeScale = prevScale;
                Cursor.lockState = prevLock;
                Cursor.visible = prevVisible;
                Release();
            }
        }

        static void Styles()
        {
            if (sHead != null) return;
            sHead = new GUIStyle(GUI.skin.label); sHead.fontSize = 20; sHead.fontStyle = FontStyle.Bold;
            sHead.normal.textColor = new Color(0.22f, 0.88f, 0.78f);
            sDim = new GUIStyle(GUI.skin.label); sDim.fontSize = 12; sDim.normal.textColor = new Color(0.6f, 0.63f, 0.7f); sDim.wordWrap = true;
            sAcc = new GUIStyle(GUI.skin.label); sAcc.fontStyle = FontStyle.Bold; sAcc.normal.textColor = new Color(0.22f, 0.88f, 0.78f);
            sBox = new GUIStyle(GUI.skin.box);
            var t = new Texture2D(1, 1); t.SetPixel(0, 0, new Color(0.06f, 0.08f, 0.11f, 0.97f)); t.Apply();
            sBox.normal.background = t;
        }

        internal static void OnGUI()
        {
            Event ev = Event.current;
            if (ev.type == EventType.KeyDown && (ev.keyCode == KeyCode.F9 || (ev.keyCode == KeyCode.T && ev.shift)) && GUIUtility.keyboardControl == 0)
            { Toggle(!open); ev.Use(); return; }
            if (open && ev.type == EventType.KeyDown && ev.keyCode == KeyCode.Escape) { Toggle(false); ev.Use(); return; }
            Styles();
            if (showFps) GUI.Label(new Rect(10, 8, 140, 26), "FPS " + Mathf.RoundToInt(fps), sHead);
            if (!open)
            {
                if (speed != 1f) GUI.Label(new Rect(Screen.width - 120, 8, 110, 26), speed == 0f ? "ПАУЗА" : "×" + speed.ToString("0.##"), sHead);
                return;
            }
            GUI.depth = -1000;
            float w = Mathf.Min(Screen.width - 40, 1100), h = Screen.height - 60;
            var win = new Rect((Screen.width - w) / 2, 30, w, h);
            GUI.Box(win, "", sBox);
            GUILayout.BeginArea(new Rect(win.x + 14, win.y + 10, w - 28, h - 20));
            GUILayout.BeginHorizontal();
            GUILayout.Label("TEST MENU  |  " + Application.productName, sHead);
            GUILayout.FlexibleSpace();
            if (GUILayout.Button("Обновить", GUILayout.Width(110))) Refresh();
            if (GUILayout.Button("Закрыть", GUILayout.Width(110))) { Toggle(false); GUILayout.EndHorizontal(); GUILayout.EndArea(); return; }
            GUILayout.EndHorizontal();
            GUILayout.BeginHorizontal();
            string[,] tabs = { { "main", "Главное" }, { "vars", "Все переменные" }, { "game", "Игра" }, { "scan", "Поиск" }, { "help", "Справка" } };
            for (int i = 0; i < tabs.GetLength(0); i++)
                if (GUILayout.Toggle(tab == tabs[i, 0], tabs[i, 1], GUI.skin.button, GUILayout.Width(150))) { if (tab != tabs[i, 0]) scroll = Vector2.zero; tab = tabs[i, 0]; }
            GUILayout.EndHorizontal();
            tip = "";
            if (tab == "main" || tab == "vars") DrawVars(tab == "main");
            else if (tab == "game") DrawGame();
            else if (tab == "scan") DrawScan();
            else DrawHelp();
            GUILayout.FlexibleSpace();
            GUILayout.Label(tip != "" ? tip : "Shift+T / F9 — меню   |   Esc — закрыть   |   F7 — UnityExplorer   |   игра на паузе", sDim);
            GUILayout.EndArea();
        }

        static void DrawVars(bool main)
        {
            GUILayout.BeginHorizontal();
            GUILayout.Label("фильтр:", GUILayout.Width(60));
            filter = GUILayout.TextField(filter, GUILayout.Width(260));
            GUILayout.Space(16);
            GUILayout.Label("шаг:", GUILayout.Width(36));
            foreach (int s in new[] { 1, 10, 100, 1000 })
                if (GUILayout.Toggle(step == s, s.ToString(), GUI.skin.button, GUILayout.Width(56))) step = s;
            GUILayout.FlexibleSpace();
            if (frozen.Count > 0 && GUILayout.Button("снять заморозки (" + frozen.Count + ")")) frozen.Clear();
            GUILayout.EndHorizontal();
            string q = filter.Trim().ToLowerInvariant();
            var groups = new List<string>();
            var byGroup = new Dictionary<string, List<Entry>>();
            foreach (Entry e in entries)
            {
                if (main && !e.Stat && !frozen.ContainsKey(e.Path)) continue;
                if (q != "" && e.Label.ToLowerInvariant().IndexOf(q) < 0 && e.Path.ToLowerInvariant().IndexOf(q) < 0) continue;
                List<Entry> l;
                if (!byGroup.TryGetValue(e.Group, out l)) { l = new List<Entry>(); byGroup[e.Group] = l; groups.Add(e.Group); }
                l.Add(e);
            }
            // группы со статами — выше
            groups.Sort(delegate (string a, string b) { return Count(byGroup[b]).CompareTo(Count(byGroup[a])); });
            scroll = GUILayout.BeginScrollView(scroll);
            if (groups.Count == 0)
                GUILayout.Label(entries.Count == 0 ? "Объекты игры не найдены — загрузи сохранение и нажми «Обновить»." : "Ничего не подходит под фильтр.", sDim);
            int shown = 0;
            foreach (string g in groups)
            {
                bool isOpen = main || q != "" || openGroups.Contains(g) || groups.Count <= 3;
                if (GUILayout.Button((isOpen ? "▾ " : "▸ ") + g + "   (" + byGroup[g].Count + ")", GUI.skin.label)) { if (!openGroups.Remove(g)) openGroups.Add(g); }
                if (!isOpen) continue;
                foreach (Entry e in byGroup[g])
                {
                    if (++shown > 400) break;
                    DrawRow(e);
                }
            }
            if (shown > 400) GUILayout.Label("Показаны первые 400 — сузь фильтром.", sDim);
            GUILayout.EndScrollView();
        }

        static int Count(List<Entry> l) { int n = 0; foreach (Entry e in l) if (e.Stat) n++; return n; }

        static void DrawRow(Entry e)
        {
            object v = e.Get();
            GUILayout.BeginHorizontal();
            GUILayout.Label(new GUIContent(e.Label, e.Path), GUILayout.Width(320));
            if (Event.current.type == EventType.Repaint && GUILayoutUtility.GetLastRect().Contains(Event.current.mousePosition)) tip = e.Path;
            string cur;
            if (!edit.TryGetValue(e.Path, out cur)) cur = v == null ? "" : Convert.ToString(v, System.Globalization.CultureInfo.InvariantCulture);
            string nv = GUILayout.TextField(cur, GUILayout.Width(200));
            if (nv != cur) edit[e.Path] = nv;
            if (edit.ContainsKey(e.Path) && GUILayout.Button("записать", GUILayout.Width(90)))
            {
                try
                {
                    object val = e.Type.IsEnum ? Enum.Parse(e.Type, edit[e.Path]) : Convert.ChangeType(edit[e.Path], e.Type, System.Globalization.CultureInfo.InvariantCulture);
                    Put(e, val);
                }
                catch { }
                edit.Remove(e.Path);
            }
            if (e.IsNum)
            {
                if (GUILayout.Button("−", GUILayout.Width(36))) Put(e, Convert.ToDouble(v) - step);
                if (GUILayout.Button("+", GUILayout.Width(36))) Put(e, Convert.ToDouble(v) + step);
            }
            else if (e.Type == typeof(bool))
            {
                if (GUILayout.Button("вкл/выкл", GUILayout.Width(90))) Put(e, !(v is bool && (bool)v));
            }
            else if (e.Type.IsEnum)
            {
                if (GUILayout.Button("следующее", GUILayout.Width(110)))
                {
                    Array vals = Enum.GetValues(e.Type);
                    int i = Array.IndexOf(vals, v);
                    Put(e, vals.GetValue((i + 1) % vals.Length));
                }
            }
            bool fz = frozen.ContainsKey(e.Path);
            if (GUILayout.Toggle(fz, "заморозить", GUI.skin.button, GUILayout.Width(110)) != fz)
            {
                if (fz) frozen.Remove(e.Path); else frozen[e.Path] = e.Get();
            }
            GUILayout.EndHorizontal();
        }

        static void Put(Entry e, object v)
        {
            e.Set(v);
            if (frozen.ContainsKey(e.Path)) frozen[e.Path] = e.Get();
            edit.Remove(e.Path);
        }

        // ---- «Игра»: темп, профиль, телепорт
        static GameObject Player()
        {
            try { GameObject go = GameObject.FindWithTag("Player"); if (go != null) return go; } catch { }
            foreach (string n in new[] { "Player", "player", "Hero", "PlayerCharacter", "FPSController", "ThirdPersonController" })
            {
                try { GameObject go = GameObject.Find(n); if (go != null) return go; } catch { }
            }
            return null;
        }

        static void SyncPhysics()
        {
            foreach (string t in new[] { "UnityEngine.Physics, UnityEngine.PhysicsModule", "UnityEngine.Physics, UnityEngine",
                                         "UnityEngine.Physics2D, UnityEngine.Physics2DModule" })
            {
                try
                {
                    Type ty = Type.GetType(t);
                    MethodInfo m = ty == null ? null : ty.GetMethod("SyncTransforms", Type.EmptyTypes);
                    if (m != null) m.Invoke(null, null);
                }
                catch { }
            }
        }

        static string V3(Vector3 v) { return "(" + v.x.ToString("0.#") + ", " + v.y.ToString("0.#") + ", " + v.z.ToString("0.#") + ")"; }

        static void DrawGame()
        {
            scroll = GUILayout.BeginScrollView(scroll);
            GUILayout.Label("Скорость игры", sAcc);
            GUILayout.BeginHorizontal();
            float[] ks = { 0f, 0.25f, 0.5f, 1f, 2f, 3f, 5f };
            foreach (float k in ks)
                if (GUILayout.Toggle(Mathf.Approximately(speed, k), k == 0f ? "пауза" : "×" + k.ToString("0.##"), GUI.skin.button, GUILayout.Width(90)) && !Mathf.Approximately(speed, k))
                { speed = k; prevScale = k; }
            GUILayout.EndHorizontal();
            GUILayout.Label("Темп включится после закрытия меню (пока меню открыто, игра на паузе); пока он не ×1, в углу виден значок.", sDim);
            GUILayout.BeginHorizontal();
            if (GUILayout.Button(new GUIContent("Шаг кадра", "Игра на паузе продвигается ровно на один кадр"), GUILayout.Width(200)))
            { speed = 0f; prevScale = 0f; stepState = 1; }
            showFps = GUILayout.Toggle(showFps, showFps ? "FPS в углу: вкл" : "FPS в углу: выкл", GUI.skin.button, GUILayout.Width(200));
            GUILayout.Label("сейчас " + Mathf.RoundToInt(fps) + " кадров/с", sDim);
            GUILayout.EndHorizontal();
            GUILayout.Space(10);
            GUILayout.Label("Профиль игры", sAcc);
            GUILayout.BeginHorizontal();
            if (GUILayout.Button("Сохранить профиль", GUILayout.Width(200))) Profile.Save(true, speed, frozen);
            if (Profile.Has && GUILayout.Button("Удалить профиль", GUILayout.Width(200))) Profile.Save(false, speed, frozen);
            GUILayout.Label(Profile.Has ? "профиль есть: темп и заморозки ставятся сами при запуске" : "профиля нет", sDim);
            GUILayout.EndHorizontal();
            GUILayout.Space(10);
            GUILayout.Label("Игрок и точки телепорта", sAcc);
            GameObject p = Player();
            if (p == null) GUILayout.Label("Игрок не найден: нет объекта с тегом Player или с именем Player / Hero.", sDim);
            else
            {
                Vector3 pos = p.transform.position;
                GUILayout.BeginHorizontal();
                GUILayout.Label(p.name + ": " + V3(pos), GUILayout.Width(420));
                if (GUILayout.Button("Запомнить место", GUILayout.Width(180)))
                    places.Add(new KeyValuePair<string, Vector3>(UnityEngine.SceneManagement.SceneManager.GetActiveScene().name + "  " + V3(pos), pos));
                GUILayout.EndHorizontal();
                for (int i = 0; i < places.Count; i++)
                {
                    GUILayout.BeginHorizontal();
                    GUILayout.Label(places[i].Key, GUILayout.Width(420));
                    if (GUILayout.Button("сюда", GUILayout.Width(90))) { p.transform.position = places[i].Value; SyncPhysics(); Toggle(false); GUILayout.EndHorizontal(); break; }
                    if (GUILayout.Button("×", GUILayout.Width(40))) { places.RemoveAt(i); GUILayout.EndHorizontal(); break; }
                    GUILayout.EndHorizontal();
                }
            }
            GUILayout.EndScrollView();
        }

        // ---- поиск значения
        static Dictionary<string, double> Numbers()
        {
            var d = new Dictionary<string, double>();
            foreach (Entry e in entries)
                if (e.IsNum) { object v = e.Get(); if (v != null) d[e.Path] = Convert.ToDouble(v); }
            return d;
        }

        static void DrawScan()
        {
            GUILayout.Label("Как ArtMoney, но по именам: «Снимок» → закрой меню, измени значение в игре → сужай.", sDim);
            GUILayout.BeginHorizontal();
            if (GUILayout.Button("Снимок", GUILayout.Width(120))) { Refresh(); snap = Numbers(); cands = new List<string>(snap.Keys); scanMsg = "Снимок: " + cands.Count + " чисел."; }
            string[] modes = { "изменились", "не изменились", "больше", "меньше" };
            for (int m = 0; m < modes.Length; m++)
                if (GUILayout.Button(modes[m], GUILayout.Width(140))) Narrow(m);
            GUILayout.EndHorizontal();
            GUILayout.Label(scanMsg, sAcc);
            if (cands.Count == 0 || cands.Count > 80) return;
            var by = new Dictionary<string, Entry>();
            foreach (Entry e in entries) if (!by.ContainsKey(e.Path)) by[e.Path] = e;
            scroll = GUILayout.BeginScrollView(scroll);
            foreach (string pth in cands) { Entry e; if (by.TryGetValue(pth, out e)) DrawRow(e); }
            GUILayout.EndScrollView();
        }

        static void Narrow(int mode)
        {
            if (snap.Count == 0) { scanMsg = "Сначала «Снимок»."; return; }
            Refresh();
            var now = Numbers();
            var keep = new List<string>();
            foreach (string p in cands)
            {
                double a, b;
                if (!snap.TryGetValue(p, out a) || !now.TryGetValue(p, out b)) continue;
                if (mode == 0 ? b != a : mode == 1 ? b == a : mode == 2 ? b > a : b < a) keep.Add(p);
            }
            cands = keep;
            snap = now;
            scanMsg = "Осталось: " + keep.Count + (keep.Count > 80 ? " (покажу, когда будет ≤ 80)" : "");
        }

        static void DrawHelp()
        {
            string[] lines = {
                "Shift+T или F9 — открыть, Esc — закрыть. Пока меню открыто, игра на паузе.",
                "Главное: поля, похожие на статы (деньги, здоровье, опыт…). Все переменные: всё найденное, группы по объектам.",
                "Поле значения — впиши число и «записать»; −/+ с шагом; «заморозить» — игра не сможет изменить значение.",
                "Игра: скорость (пауза … ×5), профиль (темп и заморозки при каждом запуске), телепорт игрока.",
                "Поиск: «Снимок», закрой меню, измени значение в игре, вернись и жми «изменились» / «больше» / «меньше».",
                "«Обновить» — после загрузки сохранения или смены сцены. F7 — UnityExplorer: все объекты и поля.",
                "Перед экспериментами сохранись в игре.",
            };
            foreach (string l in lines) GUILayout.Label(l, sDim);
        }
    }
}
