import time

_IMPORT_T0 = time.perf_counter()  # package import time, reported by perf diagnostics when they are on

from pathlib import Path  # noqa: E402

from dotenv import load_dotenv  # noqa: E402

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from agent_engine.cli import main  # noqa: E402  (after .env is loaded)

__all__ = ["main"]
