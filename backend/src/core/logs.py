import os
import sys
import io
import logging
from datetime import datetime

from src.config import get_settings

settings = get_settings()

logs_path = os.path.join(os.getcwd(), 'logs')
os.makedirs(logs_path, exist_ok=True)


logging_str = (
    "[ %(asctime)s ] [%(name)s] | Module: %(module)s |" 
    "Function: %(funcName)s | Line: %(lineno)d - %(levelname)s - %(message)s"
)

stdout_stream = sys.stdout
try:
    if getattr(sys.stdout, "encoding", "").lower() != "utf-8":
        stdout_stream = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
except Exception:
    stdout_stream = sys.stdout

logging.basicConfig(
    format=logging_str,
    level=settings.log_level,
    handlers=[
        logging.FileHandler(f"{settings.log_file}", mode='a', encoding='utf-8'),
        logging.StreamHandler(stdout_stream),
    ],
)

logger = logging.getLogger("researchmind")

