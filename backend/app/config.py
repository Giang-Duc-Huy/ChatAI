import os
from pathlib import Path
from dotenv import load_dotenv

PROJECT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT / ".env")
DATA_RAW = PROJECT / "data" / "raw"
CATALOG = PROJECT / "data" / "catalog.csv"
INDEX_DIR = PROJECT / "data" / "processed" / "chroma"
LOG_FILE = PROJECT / "logs" / "latency.jsonl"
FRONTEND_SRC = PROJECT / "frontend"
FRONTEND = FRONTEND_SRC / "dist" if (FRONTEND_SRC / "dist" / "index.html").exists() else FRONTEND_SRC

ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "claude-sonnet-5-5")
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "BAAI/bge-m3")
TOP_K = int(os.getenv("TOP_K", "5"))
MIN_SCORE = float(os.getenv("MIN_SCORE", "0.35"))
WHISPER_MODEL = os.getenv("WHISPER_MODEL", "medium")
TTS_VOICE = os.getenv("TTS_VOICE", "vi-VN-HoaiMyNeural")
RATE_LIMIT_PER_MIN = int(os.getenv("RATE_LIMIT_PER_MIN", "20"))
PRICE_IN = float(os.getenv("PRICE_IN_PER_M", "3"))
PRICE_OUT = float(os.getenv("PRICE_OUT_PER_M", "15"))
