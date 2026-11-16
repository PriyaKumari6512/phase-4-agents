"""Delegate to uv_build, bundling the checkout's single source of agent assets.

The temporary package data is removed after each build. No second maintained copy
of prompts, catalogs or examples is checked in.
"""
from contextlib import contextmanager
from pathlib import Path
import shutil
import uv_build

ROOT = Path(__file__).resolve().parent


@contextmanager
def bundled():
    target = ROOT / "src" / "agent_engine" / "_assets"
    if target.exists():
        raise RuntimeError("temporary build assets already exist; concurrent builds in one checkout are unsupported")
    try:
        target.mkdir()
        for name in ("agents", "examples"):
            shutil.copytree(ROOT / name, target / name)
        shutil.copyfile(ROOT / "gates.toml", target / "gates.toml")
        yield
    finally:
        shutil.rmtree(target, ignore_errors=True)


def build_wheel(wheel_directory, config_settings=None, metadata_directory=None):
    with bundled():
        return uv_build.build_wheel(wheel_directory, config_settings, metadata_directory)


def build_sdist(sdist_directory, config_settings=None):
    return uv_build.build_sdist(sdist_directory, config_settings)


def build_editable(wheel_directory, config_settings=None, metadata_directory=None):
    return uv_build.build_editable(wheel_directory, config_settings, metadata_directory)
