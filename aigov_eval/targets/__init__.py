"""Target adapter registry."""

from __future__ import annotations

from typing import Any, Dict, Type

from .base import TargetAdapter
from .mock_llm import MockTargetAdapter
from .scripted import ScriptedMockTargetAdapter


TARGETS: Dict[str, Type[TargetAdapter]] = {
    MockTargetAdapter.name: MockTargetAdapter,
    ScriptedMockTargetAdapter.name: ScriptedMockTargetAdapter,
}


def get_target(name: str) -> Type[TargetAdapter]:
    if name not in TARGETS:
        raise KeyError(f"Unknown target adapter: {name}")
    return TARGETS[name]
