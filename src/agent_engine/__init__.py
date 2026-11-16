from pathlib import Path

from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parents[2] / ".env")

from agent_engine.cli import main  # noqa: E402  (after .env is loaded)

__all__ = ["main"]
