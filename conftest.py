"""Pytest configuration for default scope."""

from __future__ import annotations

import os
from pathlib import Path


def pytest_ignore_collect(collection_path: Path, config):  # type: ignore[override]
    if os.getenv("AIGOV_RUN_JUDGE_TESTS") == "1":
        return False
    path_str = str(collection_path)
    return "tests\\judge" in path_str or "tests/judge" in path_str
