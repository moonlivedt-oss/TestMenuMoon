// Заглушка UnityEngine (только API, которым пользуется engines/unity/mono/TestMenuMono.cs):
// тест собирает её в UnityEngine.dll и проверяет, что плагин компилируется тем же csc.exe,
// что и при установке в игру. Поведения здесь нет — только сигнатуры как в Unity.
using System;

namespace UnityEngine
{
    public class Object
    {
        public string name;
        public static Object[] FindObjectsOfType(Type t) { return new Object[0]; }
        public static bool operator ==(Object a, Object b) { return ReferenceEquals(a, b); }
        public static bool operator !=(Object a, Object b) { return !ReferenceEquals(a, b); }
        public override bool Equals(object o) { return ReferenceEquals(this, o); }
        public override int GetHashCode() { return 0; }
    }
    public class Component : Object { public Transform transform; }
    public class Behaviour : Component { public bool enabled; }
    public class MonoBehaviour : Behaviour { }
    public class ScriptableObject : Object { }
    public class Transform : Component { public Vector3 position; }
    public class GameObject : Object
    {
        public Transform transform;
        public static GameObject FindWithTag(string t) { return null; }
        public static GameObject Find(string n) { return null; }
    }
    public static class Resources { public static Object[] FindObjectsOfTypeAll(Type t) { return new Object[0]; } }
    public static class Time { public static float timeScale; public static float realtimeSinceStartup; public static float unscaledDeltaTime; }
    public static class Mathf
    {
        public static float Min(float a, float b) { return a < b ? a : b; }
        public static bool Approximately(float a, float b) { return Math.Abs(a - b) < 1e-6; }
        public static float Lerp(float a, float b, float t) { return a + (b - a) * t; }
        public static int RoundToInt(float f) { return (int)Math.Round(f); }
    }
    public enum CursorLockMode { None, Locked, Confined }
    public static class Cursor { public static CursorLockMode lockState; public static bool visible; }
    public static class Application { public static string productName; }
    public static class Screen { public static int width; public static int height; }
    public struct Vector2 { public float x, y; public static Vector2 zero; }
    public struct Vector3 { public float x, y, z; }
    public struct Color { public Color(float r, float g, float b) { } public Color(float r, float g, float b, float a) { } }
    public struct Rect
    {
        public Rect(float x, float y, float w, float h) { this.x = x; this.y = y; width = w; height = h; }
        public float x, y, width, height;
        public bool Contains(Vector2 p) { return false; }
    }
    public class Texture { }
    public class Texture2D : Texture { public Texture2D(int w, int h) { } public void SetPixel(int x, int y, Color c) { } public void Apply() { } }
    public enum FontStyle { Normal, Bold }
    public class GUIStyleState { public Color textColor; public Texture2D background; }
    public class GUIStyle
    {
        public GUIStyle() { }
        public GUIStyle(GUIStyle o) { }
        public int fontSize; public FontStyle fontStyle; public bool wordWrap;
        public GUIStyleState normal = new GUIStyleState();
    }
    public class GUISkin { public GUIStyle label, box, button; }
    public class GUIContent { public GUIContent(string text, string tooltip) { } }
    public sealed class GUILayoutOption { }
    public enum EventType { MouseDown, KeyDown, Repaint }
    public enum KeyCode { None, T, F9, Escape }
    public class Event
    {
        public static Event current;
        public EventType type; public KeyCode keyCode; public bool shift; public Vector2 mousePosition;
        public void Use() { }
    }
    public static class GUIUtility { public static int keyboardControl; }
    public static class GUI
    {
        public static GUISkin skin; public static int depth;
        public static void Box(Rect r, string t, GUIStyle s) { }
        public static void Label(Rect r, string t, GUIStyle s) { }
    }
    public static class GUILayoutUtility { public static Rect GetLastRect() { return new Rect(); } }
    public static class GUILayout
    {
        public static void BeginArea(Rect r) { }
        public static void EndArea() { }
        public static void BeginHorizontal(params GUILayoutOption[] o) { }
        public static void EndHorizontal() { }
        public static void Label(string t, params GUILayoutOption[] o) { }
        public static void Label(string t, GUIStyle s, params GUILayoutOption[] o) { }
        public static void Label(GUIContent c, params GUILayoutOption[] o) { }
        public static bool Button(string t, params GUILayoutOption[] o) { return false; }
        public static bool Button(GUIContent c, params GUILayoutOption[] o) { return false; }
        public static bool Button(string t, GUIStyle s, params GUILayoutOption[] o) { return false; }
        public static bool Toggle(bool v, string t, GUIStyle s, params GUILayoutOption[] o) { return v; }
        public static string TextField(string t, params GUILayoutOption[] o) { return t; }
        public static void FlexibleSpace() { }
        public static void Space(float px) { }
        public static GUILayoutOption Width(float w) { return null; }
        public static Vector2 BeginScrollView(Vector2 p, params GUILayoutOption[] o) { return p; }
        public static void EndScrollView() { }
    }
}

namespace UnityEngine.SceneManagement
{
    public struct Scene { public string name; }
    public static class SceneManager { public static Scene GetActiveScene() { return new Scene(); } }
}
