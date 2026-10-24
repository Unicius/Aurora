import os
from dotenv import load_dotenv

# Resolve .env relative to this file so it works both inside STE Slicer
# (where the CWD is the slicer's install dir) and in standalone mode.
_PLUGIN_DIR = os.path.dirname(os.path.abspath(__file__))
_ENV_PATH = os.path.join(_PLUGIN_DIR, ".env")

load_dotenv(_ENV_PATH, override=False)

LLM_API_URL = os.getenv("LLM_API_URL", "https://api.openai.com/v1")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_MODEL_NAME = os.getenv("LLM_MODEL_NAME", "gpt-4o")
