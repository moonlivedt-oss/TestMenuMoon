// TestMenuMoon: меню для игр GameMaker 2.3+ (UndertaleModTool CLI).
// Запускает engines/gamemaker/inject.py:
//   UndertaleModCli load data.win.tm_bak -s TestMenu.csx -o data.win -f
// Код меню — menu_create.gml / menu_step.gml / menu_draw.gml рядом с этим скриптом
// (inject.py подставляет их в TM_GML_* ниже). Объект obj_tm_menu — постоянный, ставится
// в первую комнату игры.
using System;
using System.Linq;
using UndertaleModLib.Models;

EnsureDataLoaded();

if (!Data.IsVersionAtLeast(2, 3))
    throw new ScriptException("TestMenuMoon: нужна игра на GameMaker 2.3+ (версия данных " +
                              Data.GeneralInfo.Major + "." + Data.GeneralInfo.Minor + ")");
if (Data.GameObjects.ByName("obj_tm_menu") != null)
    throw new ScriptException("TestMenuMoon: меню уже внутри data.win (ставить нужно в оригинал)");

string TM_GML_CREATE = @"%CREATE%";
string TM_GML_STEP = @"%STEP%";
string TM_GML_DRAW = @"%DRAW%";

var obj = new UndertaleGameObject()
{
    Name = Data.Strings.MakeString("obj_tm_menu"),
    Persistent = true,
    Visible = true,
};
Data.GameObjects.Add(obj);

var importGroup = new UndertaleModLib.Compiler.CodeImportGroup(Data);
importGroup.QueueReplace(obj.EventHandlerFor(EventType.Create, Data), TM_GML_CREATE);
importGroup.QueueReplace(obj.EventHandlerFor(EventType.Step, EventSubtypeStep.Step, Data), TM_GML_STEP);
importGroup.QueueReplace(obj.EventHandlerFor(EventType.Draw, EventSubtypeDraw.DrawGUI, Data), TM_GML_DRAW);
importGroup.Import();

// экземпляр — в первую комнату игры (в GameMaker 2 — ещё и в её слой экземпляров)
var first = Data.GeneralInfo.RoomOrder[0].Resource;
var inst = new UndertaleRoom.GameObject()
{
    InstanceID = Data.GeneralInfo.LastObj++,
    ObjectDefinition = obj,
    X = 0,
    Y = 0,
};
first.GameObjects.Add(inst);
var layer = first.Layers.FirstOrDefault(l => l.LayerType == UndertaleRoom.LayerType.Instances);
if (layer == null)
    throw new ScriptException("TestMenuMoon: в первой комнате (" + first.Name.Content + ") нет слоя экземпляров");
layer.InstancesData.Instances.Add(inst);
