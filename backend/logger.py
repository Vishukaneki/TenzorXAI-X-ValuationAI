"""
logger.py
---------
Centralized logging configuration for the TenzorXAI backend.

Log levels:
  DEBUG   → detailed internals (feature values, scores, SHAP weights)
  INFO    → normal request lifecycle (startup, request in/out, timings)
  WARNING → unexpected but recoverable situations (fallbacks, missing data)
  ERROR   → exceptions and failures that affect the response

Log output:
  - Console (stdout) — colored, human-readable
  - File (logs/backend.log) — JSON lines, one per log record, easy to grep

Usage in any module:
    from logger import get_logger
    logger = get_logger(__name__)
    logger.info("Something happened")
    logger.debug("feature_vector=%s", features)
    logger.error("Prediction failed", exc_info=True)
"""

import logging
import logging.handlers
import json
import os
import sys
from datetime import datetime, timezone

# ── PATHS ─────────────────────────────────────────────────────────────────────
LOG_DIR  = os.path.join(os.path.dirname(__file__), "logs")
LOG_FILE = os.path.join(LOG_DIR, "backend.log")
os.makedirs(LOG_DIR, exist_ok=True)

# ── LEVEL (override with LOG_LEVEL env var) ───────────────────────────────────
_level_name = os.getenv("LOG_LEVEL", "DEBUG").upper()
LOG_LEVEL   = getattr(logging, _level_name, logging.DEBUG)


# ── JSON LINE FORMATTER (for file output) ─────────────────────────────────────
class _JsonFormatter(logging.Formatter):
    """Emit one JSON object per log record — easy to grep / import into tools."""

    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "ts":      datetime.now(timezone.utc).isoformat(),
            "level":   record.levelname,
            "logger":  record.name,
            "message": record.getMessage(),
            "module":  record.module,
            "func":    record.funcName,
            "line":    record.lineno,
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


# ── COLORED CONSOLE FORMATTER ─────────────────────────────────────────────────
_COLORS = {
    "DEBUG":    "\033[36m",   # cyan
    "INFO":     "\033[32m",   # green
    "WARNING":  "\033[33m",   # yellow
    "ERROR":    "\033[31m",   # red
    "CRITICAL": "\033[35m",   # magenta
}
_RESET = "\033[0m"


class _ColorFormatter(logging.Formatter):
    FMT = "%(asctime)s  {color}%(levelname)-8s{reset}  %(name)s  %(message)s"

    def format(self, record: logging.LogRecord) -> str:
        color = _COLORS.get(record.levelname, "")
        fmt   = self.FMT.format(color=color, reset=_RESET)
        formatter = logging.Formatter(fmt, datefmt="%H:%M:%S")
        return formatter.format(record)


# ── ROOT LOGGER SETUP (called once on import) ─────────────────────────────────
def _setup() -> None:
    root = logging.getLogger("tenzor")
    if root.handlers:          # already configured (e.g. imported twice)
        return

    root.setLevel(LOG_LEVEL)

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setLevel(LOG_LEVEL)
    ch.setFormatter(_ColorFormatter())
    root.addHandler(ch)

    # Rotating file handler (10 MB × 5 backups → max 50 MB)
    fh = logging.handlers.RotatingFileHandler(
        LOG_FILE,
        maxBytes=10 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    fh.setLevel(LOG_LEVEL)
    fh.setFormatter(_JsonFormatter())
    root.addHandler(fh)

    root.info(
        "Logging initialised  level=%s  file=%s",
        _level_name, LOG_FILE,
    )


_setup()


def get_logger(name: str) -> logging.Logger:
    """
    Return a child logger under the 'tenzor' namespace.

    Example:
        logger = get_logger(__name__)   # → 'tenzor.main', 'tenzor.engine_modules', …
    """
    # Strip the package prefix so the logger tree is always rooted at 'tenzor'
    short = name.replace("backend.", "")
    return logging.getLogger(f"tenzor.{short}")
