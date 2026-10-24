"""
Aurora Plugin — Standalone smoke test.

Runs WITHOUT STE Slicer installed. Tests:
  1. Config loading
  2. GeometryAnalyzer (trimesh or fallback)
  3. StressAnalyzer   (FEA killer feature)
  4. SlicerAPI        (console-log mode)
  5. ToolsRegistry dispatch
  6. Agent loop       (requires LLM_API_KEY in .env)
  7. PyQt5 UI launch  (optional — pass --ui flag)

Usage:
    python test_standalone.py                         # core tests only
    python test_standalone.py --ui                    # also opens chat window
    python test_standalone.py --stl path/to/model.stl # test with real STL
    python test_standalone.py --stl model.stl --ui    # full test
"""

import sys
import os
import json
import argparse

# ── Project root on sys.path ───────────────────────────────────────────────
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, "plugin", ".env"), override=False)
load_dotenv(os.path.join(ROOT, ".env"), override=False)

PASS = "\033[92m✓\033[0m"
FAIL = "\033[91m✗\033[0m"
INFO = "\033[94mℹ\033[0m"
WARN = "\033[93m⚠\033[0m"


def section(title: str):
    print(f"\n\033[1m{'─' * 52}\n  {title}\n{'─' * 52}\033[0m")


# ── 1. Config ──────────────────────────────────────────────────────────────
def test_config():
    section("1. Config (.env)")
    from plugin.config import LLM_API_URL, LLM_API_KEY, LLM_MODEL_NAME
    print(f"  {INFO} LLM_API_URL    = {LLM_API_URL}")
    print(f"  {INFO} LLM_MODEL_NAME = {LLM_MODEL_NAME}")
    has_key = bool(LLM_API_KEY and LLM_API_KEY != "your_api_key_here")
    if has_key:
        print(f"  {PASS} API key найден")
    else:
        print(f"  {WARN}  API key не задан — тест агента будет пропущен")
    return has_key


# ── 2. GeometryAnalyzer ────────────────────────────────────────────────────
def test_geometry(stl_path=None):
    section("2. GeometryAnalyzer")
    from plugin.mcp_tools.geometry_analyzer import GeometryAnalyzer
    result = GeometryAnalyzer.analyze_stl(stl_path or "__demo__")
    print(f"  {PASS} Режим: {result['recommended_mode']}")
    print(f"  {PASS} Причина: {result['reason']}")
    print(f"  {INFO} Нависания: {result.get('overhang_percentage', 'n/a')}%")
    if stl_path:
        dims = result.get("dimensions_mm", {})
        print(f"  {INFO} Размеры: {dims.get('x')}×{dims.get('y')}×{dims.get('z')} мм")
    return result


# ── 3. StressAnalyzer ──────────────────────────────────────────────────────
def test_stress(stl_path=None):
    section("3. StressAnalyzer (Killer Feature 🌡️)")
    from plugin.mcp_tools.stress_analyzer import StressAnalyzer
    result = StressAnalyzer.analyze(stl_path or "__demo__", [0, 0, -1])
    s = result.get("summary", {})
    print(f"  {PASS} Высокий стресс: {s.get('high_stress_pct', 0):.1f}% граней → инфилл 80%")
    print(f"  {PASS} Ср. адаптивный инфилл: {s.get('adaptive_avg_infill', 0):.1f}%")
    print(f"  {PASS} Экономия материала: ~{s.get('material_savings_pct', 0):.0f}%")
    print(f"  {PASS} Экономия времени:   ~{s.get('time_savings_pct', 0):.0f}%")
    zones = result.get("adaptive_infill_profile", [])
    print(f"  {INFO} Z-зон адаптивного инфилла: {len(zones)}")
    orient = result.get("recommended_orientation", {})
    print(f"  {INFO} Оптимальная ориентация: {orient.get('reason', '')}")
    return result


# ── 4. SlicerAPI ───────────────────────────────────────────────────────────
def test_slicer_api():
    section("4. SlicerAPI (console mode, printing_mode=classic/cylindrical)")
    from plugin.mcp_tools.slicer_api import SlicerAPI

    r = SlicerAPI.set_print_mode("5D")
    assert r["success"], f"set_print_mode failed: {r}"
    assert r.get("printing_mode") == "cylindrical", f"Wrong key value: {r}"
    print(f"  {PASS} set_print_mode('5D') → printing_mode='cylindrical'")

    r = SlicerAPI.set_print_mode("3D")
    assert r["success"] and r.get("printing_mode") == "classic"
    print(f"  {PASS} set_print_mode('3D') → printing_mode='classic'")

    r = SlicerAPI.apply_print_profile(
        material="PETG", layer_height=0.15, print_speed=45,
        infill=40, supports=False, mode="5D"
    )
    assert r["success"], f"apply_print_profile failed: {r}"
    print(f"  {PASS} apply_print_profile PETG/5D — temp={r['temperature']}°C")

    r = SlicerAPI.apply_adaptive_infill([
        {"z_from_mm": 0,  "z_to_mm": 10, "infill_pct": 80, "stress_level": "high"},
        {"z_from_mm": 10, "z_to_mm": 30, "infill_pct": 15, "stress_level": "low"},
    ])
    assert r["success"]
    print(f"  {PASS} apply_adaptive_infill — ср. инфилл {r['avg_infill_pct']}%")

    r = SlicerAPI.start_slicing()
    assert r["success"]
    print(f"  {PASS} start_slicing")


# ── 5. ToolsRegistry ──────────────────────────────────────────────────────
def test_tools_registry():
    section("5. ToolsRegistry dispatch (9 инструментов)")
    from plugin.core.tools_registry import dispatch_tool, TOOLS_SCHEMA

    names = [t["function"]["name"] for t in TOOLS_SCHEMA]
    print(f"  {INFO} Зарегистрировано инструментов: {len(names)}")
    for n in names:
        print(f"       • {n}")

    raw = dispatch_tool("set_print_mode", {"mode": "3D"})
    result = json.loads(raw)
    assert result.get("success"), f"dispatch failed: {result}"
    print(f"  {PASS} dispatch_tool('set_print_mode') OK")

    raw = dispatch_tool("get_scene_info", {})
    result = json.loads(raw)
    print(f"  {PASS} dispatch_tool('get_scene_info') → {result}")


# ── 6. Agent loop ─────────────────────────────────────────────────────────
def test_agent(stl_path=None):
    section("6. Agent loop (реальный вызов LLM)")
    from plugin.core.agent import Agent

    tool_calls_seen = []

    def on_tool(name, args):
        tool_calls_seen.append(name)
        print(f"  {INFO} → инструмент: {name}")

    agent = Agent()
    if stl_path:
        query = "Кронштейн под нагрузку 30 кг. PETG, без поддержек."
    else:
        query = "Простой декоративный корпус. PLA, быстрая печать."

    print(f"  {INFO} Запрос: «{query}»")
    files = [stl_path] if stl_path else []
    reply = agent.run(query, attached_files=files, on_tool_call=on_tool)

    print(f"\n  {PASS} Ответ агента:\n")
    for line in reply.splitlines():
        print(f"      {line}")
    print(f"\n  {INFO} Вызвано инструментов: {len(tool_calls_seen)} → {tool_calls_seen}")


# ── 7. PyQt5 UI ───────────────────────────────────────────────────────────
def test_ui():
    section("7. PyQt5 UI — окно чата")
    try:
        from PyQt5.QtWidgets import QApplication
        from plugin.ui.chat_dock import ChatWindow

        app = QApplication.instance() or QApplication(sys.argv)
        win = ChatWindow()
        win.show()
        print(f"  {PASS} Окно чата открыто — закройте его чтобы тест завершился")
        sys.exit(app.exec_())
    except Exception as e:
        print(f"  {FAIL} UI ошибка: {e}")
        import traceback
        traceback.print_exc()


# ── Main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Aurora plugin smoke test")
    parser.add_argument("--ui",  action="store_true", help="Открыть окно чата")
    parser.add_argument("--stl", type=str, default=None, help="Путь к STL-файлу")
    args = parser.parse_args()

    print("\n\033[1m🤖 Aurora Plugin — Smoke Test\033[0m")
    print(f"Python: {sys.version.split()[0]}  |  CWD: {os.getcwd()}\n")

    has_key = test_config()
    test_geometry(args.stl)
    test_stress(args.stl)
    test_slicer_api()
    test_tools_registry()

    if has_key:
        test_agent(args.stl)
    else:
        print(f"\n  {WARN}  Тест агента пропущен — задайте LLM_API_KEY в plugin/.env")

    if args.ui:
        test_ui()
    else:
        print(f"\n\033[92m✅ Все тесты без UI пройдены.\033[0m")
        print(f"   Для теста UI запустите:  python test_standalone.py --ui\n")
