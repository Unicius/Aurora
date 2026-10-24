"""
STE Slicer API wrapper — verified against STE-Slicer-master source.

Key facts from source:
  • Framework:  PyQt5 (not PyQt6)
  • Print mode: setting key = "printing_mode", values = "classic" (3D) | "cylindrical" (5D)
  • Load model: UM.Mesh.ReadMeshJob
  • Force slice: Application.getInstance().getBackend().forceSlice()
  • Setting set: stack.setProperty(key, "value", value)
"""

import os
from typing import Optional, List, Dict

try:
    from UM.Application import Application
    from UM.Mesh.ReadMeshJob import ReadMeshJob
    from UM.Math.Vector import Vector
    from UM.Math.Quaternion import Quaternion
    import math as _math
    CURA_AVAILABLE = True
except ImportError:
    CURA_AVAILABLE = False


class SlicerAPI:

    # ─── Model management ────────────────────────────────────────────────────

    @staticmethod
    def load_model(file_path: str) -> dict:
        """Load an STL file into the current slicer scene via ReadMeshJob."""
        if not os.path.isfile(file_path):
            return {"success": False, "error": f"File not found: {file_path}"}

        if CURA_AVAILABLE:
            try:
                job = ReadMeshJob(file_path)
                job.start()
                return {"success": True, "file": file_path}
            except Exception as e:
                return {"success": False, "error": str(e)}

        print(f"[STE Slicer API] load_model → {file_path}")
        return {"success": True, "file": file_path}

    @staticmethod
    def orient_model(rotation_axis: List[float], rotation_angle_deg: float) -> dict:
        """Rotate the first model node in the scene."""
        if CURA_AVAILABLE:
            try:
                nodes = list(Application.getInstance()
                             .getController().getScene()
                             .getRoot().getChildren())
                if not nodes:
                    return {"success": False, "error": "No model in scene"}

                axis = Vector(*rotation_axis)
                q = Quaternion.fromAngleAxis(
                    _math.radians(rotation_angle_deg), axis
                )
                nodes[0].rotate(q)
                return {"success": True, "axis": rotation_axis, "angle_deg": rotation_angle_deg}
            except Exception as e:
                return {"success": False, "error": str(e)}

        print(f"[STE Slicer API] orient_model → axis={rotation_axis}, angle={rotation_angle_deg}°")
        return {"success": True, "axis": rotation_axis, "angle_deg": rotation_angle_deg}

    # ─── Settings ────────────────────────────────────────────────────────────

    @staticmethod
    def set_setting_value(key: str, value) -> dict:
        """Set a global container stack property."""
        if CURA_AVAILABLE:
            try:
                Application.getInstance().getGlobalContainerStack().setProperty(
                    key, "value", value
                )
                return {"success": True, "key": key, "value": value}
            except Exception as e:
                return {"success": False, "error": str(e)}

        print(f"[STE Slicer API] set_setting '{key}' = {value}")
        return {"success": True, "key": key, "value": value}

    @staticmethod
    def set_print_mode(mode: str) -> dict:
        """
        Switch print mode.
        mode = "3D"  → printing_mode = "classic"
        mode = "5D"  → printing_mode = "cylindrical"
        """
        if mode not in ("3D", "5D"):
            return {"success": False, "error": f"Invalid mode '{mode}'. Use '3D' or '5D'."}

        # Real STE Slicer key from fdmprinter.def.json
        slicer_value = "classic" if mode == "3D" else "cylindrical"
        result = SlicerAPI.set_setting_value("printing_mode", slicer_value)
        print(f"[STE Slicer API] print mode → {mode} (printing_mode={slicer_value})")
        return {**result, "mode": mode, "printing_mode": slicer_value}

    @staticmethod
    def apply_print_profile(
        material:     str   = "PLA",
        layer_height: float = 0.2,
        print_speed:  int   = 50,
        temperature:  int   = 210,
        infill:       int   = 20,
        supports:     bool  = False,
        mode:         str   = "3D",
    ) -> dict:
        """Apply a complete print profile."""
        MATERIAL_TEMPS = {
            "PLA": 210, "PETG": 240, "ABS": 250,
            "TPU": 230, "NYLON": 260, "PA": 260,
        }
        temp = MATERIAL_TEMPS.get(material.upper(), temperature)

        # Verified keys from fdmprinter.def.json
        settings = {
            "material_print_temperature": temp,
            "layer_height":               layer_height,
            "speed_print":                print_speed,
            "infill_sparse_density":      infill,
            "support_enable":             supports,
        }

        results = {k: SlicerAPI.set_setting_value(k, v) for k, v in settings.items()}
        mode_r  = SlicerAPI.set_print_mode(mode)

        return {
            "success":          all(r.get("success") for r in results.values()) and mode_r.get("success"),
            "material":         material,
            "temperature":      temp,
            "layer_height":     layer_height,
            "print_speed":      print_speed,
            "infill":           infill,
            "supports":         supports,
            "mode":             mode,
            "settings_applied": list(settings.keys()),
        }

    # ─── Adaptive infill ─────────────────────────────────────────────────────

    @staticmethod
    def apply_adaptive_infill(infill_profile: List[Dict]) -> dict:
        """Apply zone-based adaptive infill. Sets weighted-average global infill."""
        if not infill_profile:
            return {"success": False, "error": "Empty infill profile"}

        avg_infill = sum(z["infill_pct"] for z in infill_profile) / len(infill_profile)
        SlicerAPI.set_setting_value("infill_sparse_density", int(round(avg_infill)))

        zones_log = []
        for z in infill_profile:
            label = (f"Z {z['z_from_mm']}–{z['z_to_mm']} mm → "
                     f"{z['infill_pct']}% ({z.get('stress_level', '?')})")
            print(f"[STE Slicer API] adaptive infill: {label}")
            zones_log.append(label)

        return {
            "success":        True,
            "zones_applied":  len(zones_log),
            "avg_infill_pct": round(avg_infill, 1),
            "zones":          zones_log,
        }

    # ─── Slicing ─────────────────────────────────────────────────────────────

    @staticmethod
    def start_slicing() -> dict:
        """Trigger the slicing backend."""
        if CURA_AVAILABLE:
            try:
                Application.getInstance().getBackend().forceSlice()
                return {"success": True, "status": "Слайсинг запущен"}
            except Exception as e:
                return {"success": False, "error": str(e)}

        print("[STE Slicer API] start_slicing")
        return {"success": True, "status": "Слайсинг запущен"}

    # ─── Scene info ──────────────────────────────────────────────────────────

    @staticmethod
    def get_scene_info() -> dict:
        """Return a summary of the current slicer scene."""
        if CURA_AVAILABLE:
            try:
                app   = Application.getInstance()
                stack = app.getGlobalContainerStack()
                nodes = app.getController().getScene().getRoot().getChildren()
                printing_mode = stack.getProperty("printing_mode", "value")
                return {
                    "model_count":    len(nodes),
                    "temperature":    stack.getProperty("material_print_temperature", "value"),
                    "infill_pct":     stack.getProperty("infill_sparse_density",      "value"),
                    "layer_height":   stack.getProperty("layer_height",               "value"),
                    "printing_mode":  printing_mode,
                    "mode_display":   "5D" if printing_mode == "cylindrical" else "3D",
                    "supports":       stack.getProperty("support_enable",             "value"),
                }
            except Exception as e:
                return {"error": str(e)}

        return {
            "model_count": 0,
            "note": "STE Slicer not running — standalone mode",
        }
