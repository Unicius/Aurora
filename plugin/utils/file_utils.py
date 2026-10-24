import os
import base64
import shutil
import tempfile

TEMP_DIR = os.path.join(tempfile.gettempdir(), "aurora_slicer_plugin")


def _ensure_temp_dir():
    os.makedirs(TEMP_DIR, exist_ok=True)


def save_uploaded_file(src_path: str) -> str:
    """Copy a user-provided file to the plugin temp dir and return the new path."""
    _ensure_temp_dir()
    filename = os.path.basename(src_path)
    dst = os.path.join(TEMP_DIR, filename)
    shutil.copy2(src_path, dst)
    return dst


def encode_image_base64(file_path: str) -> str:
    """Read an image file and return its base64-encoded string."""
    with open(file_path, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def is_stl_file(path: str) -> bool:
    return path.lower().endswith(".stl")


def is_image_file(path: str) -> bool:
    return path.lower().endswith((".png", ".jpg", ".jpeg", ".bmp", ".gif", ".webp"))


def mime_type_for(path: str) -> str:
    ext = path.lower().rsplit(".", 1)[-1]
    mapping = {
        "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "png": "image/png", "gif": "image/gif",
        "bmp": "image/bmp", "webp": "image/webp",
    }
    return mapping.get(ext, "image/png")


def cleanup_temp():
    """Remove all temporary files created by the plugin."""
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR, ignore_errors=True)
