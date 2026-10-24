"""
MCP / OpenAI function-calling tool registry.

• TOOLS_SCHEMA — list of tool definitions passed to the LLM
• dispatch_tool(name, args) — executes a tool and returns JSON string
"""

import json
from ..mcp_tools.geometry_analyzer import GeometryAnalyzer
from ..mcp_tools.stress_analyzer import StressAnalyzer
from ..mcp_tools.slicer_api import SlicerAPI


TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "analyze_geometry",
            "description": (
                "Analyze an STL file's geometry: overhangs, dimensions, volume. "
                "Returns recommended print mode (3D or 5D) with reasoning."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the STL file.",
                    },
                    "load_direction": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "3-element vector for gravity/load direction, e.g. [0,0,-1].",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analyze_stress",
            "description": (
                "KILLER FEATURE — FEA stress heatmap. "
                "Identifies high-stress zones (red, 80% infill), medium (yellow, 40%), low (green, 15%). "
                "Returns adaptive infill profile per Z-layer and optimal print orientation. "
                "Call whenever the user mentions: load, strength, mechanical part, bracket, stress, "
                "nагрузка, прочность, кронштейн, напряжение."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Absolute path to the STL file.",
                    },
                    "load_direction": {
                        "type": "array",
                        "items": {"type": "number"},
                        "description": "Load/gravity direction vector, e.g. [0,0,-1] for vertical load.",
                    },
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_print_mode",
            "description": "Switch the slicer between 3D (standard) and 5D (multi-axis, no supports) print mode.",
            "parameters": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["3D", "5D"],
                        "description": "'3D' for standard FDM, '5D' for multi-axis no-support printing.",
                    }
                },
                "required": ["mode"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "set_print_setting",
            "description": (
                "Set a single print setting in the slicer. "
                "Common keys: layer_height, infill_sparse_density, material_print_temperature, "
                "speed_print, support_enable."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "key":   {"type": "string", "description": "Setting key."},
                    "value": {"description": "Setting value (number or boolean)."},
                },
                "required": ["key", "value"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_full_profile",
            "description": (
                "Apply a complete print profile in one call: "
                "material, temperature, speed, layer height, infill, supports, print mode."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "material":     {"type": "string",  "description": "PLA | PETG | ABS | TPU | Nylon"},
                    "layer_height": {"type": "number",  "description": "Layer height in mm (e.g. 0.2)"},
                    "print_speed":  {"type": "integer", "description": "Print speed in mm/s"},
                    "temperature":  {"type": "integer", "description": "Nozzle temperature °C (auto from material if omitted)"},
                    "infill":       {"type": "integer", "description": "Base infill 0–100 %"},
                    "supports":     {"type": "boolean", "description": "Enable support structures"},
                    "mode":         {"type": "string",  "enum": ["3D", "5D"], "description": "Print mode"},
                },
                "required": ["material"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "load_and_orient_model",
            "description": "Load an STL into the slicer scene, optionally with a rotation for optimal orientation.",
            "parameters": {
                "type": "object",
                "properties": {
                    "file_path":          {"type": "string", "description": "Path to STL file."},
                    "rotation_axis":      {"type": "array", "items": {"type": "number"}, "description": "[x,y,z] rotation axis"},
                    "rotation_angle_deg": {"type": "number", "description": "Rotation angle in degrees"},
                },
                "required": ["file_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "apply_adaptive_infill",
            "description": "Apply zone-based adaptive infill from stress analysis. Sets high infill in stress zones, low elsewhere.",
            "parameters": {
                "type": "object",
                "properties": {
                    "infill_profile": {
                        "type": "array",
                        "description": "List of infill zones from analyze_stress.",
                        "items": {
                            "type": "object",
                            "properties": {
                                "z_from_mm":    {"type": "number"},
                                "z_to_mm":      {"type": "number"},
                                "infill_pct":   {"type": "integer"},
                                "stress_level": {"type": "string"},
                            },
                        },
                    }
                },
                "required": ["infill_profile"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "start_slicing",
            "description": "Start the slicing process to generate G-code from the current scene. Call this last.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_scene_info",
            "description": "Get current slicer scene state: loaded models and active settings.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
]


def dispatch_tool(tool_name: str, arguments: dict) -> str:
    """Execute the named tool with the given arguments. Returns a JSON string."""
    try:
        if tool_name == "analyze_geometry":
            result = GeometryAnalyzer.analyze_stl(
                arguments["file_path"],
                arguments.get("load_direction"),
            )

        elif tool_name == "analyze_stress":
            result = StressAnalyzer.analyze(
                arguments["file_path"],
                arguments.get("load_direction"),
            )

        elif tool_name == "set_print_mode":
            result = SlicerAPI.set_print_mode(arguments["mode"])

        elif tool_name == "set_print_setting":
            result = SlicerAPI.set_setting_value(arguments["key"], arguments["value"])

        elif tool_name == "apply_full_profile":
            result = SlicerAPI.apply_print_profile(
                material=     arguments.get("material",     "PLA"),
                layer_height= arguments.get("layer_height", 0.2),
                print_speed=  arguments.get("print_speed",  50),
                temperature=  arguments.get("temperature",  210),
                infill=       arguments.get("infill",       20),
                supports=     arguments.get("supports",     False),
                mode=         arguments.get("mode",         "3D"),
            )

        elif tool_name == "load_and_orient_model":
            load_r = SlicerAPI.load_model(arguments["file_path"])
            if arguments.get("rotation_axis") and arguments.get("rotation_angle_deg") is not None:
                orient_r = SlicerAPI.orient_model(
                    arguments["rotation_axis"],
                    arguments["rotation_angle_deg"],
                )
                result = {"load": load_r, "orient": orient_r}
            else:
                result = {"load": load_r}

        elif tool_name == "apply_adaptive_infill":
            result = SlicerAPI.apply_adaptive_infill(arguments["infill_profile"])

        elif tool_name == "start_slicing":
            result = SlicerAPI.start_slicing()

        elif tool_name == "get_scene_info":
            result = SlicerAPI.get_scene_info()

        else:
            result = {"error": f"Unknown tool: {tool_name}"}

    except Exception as e:
        result = {"error": f"Tool execution failed: {e}"}

    return json.dumps(result, ensure_ascii=False, default=str)
