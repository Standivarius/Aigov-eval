"""DEPRECATED: Target adapters are EP-owned. Canonical implementation lives in aigov-mvp/aigov_ep/targets.
This registry prefers aigov_ep.targets when installed; otherwise falls back to local for CI stability."""

from __future__ import annotations

from typing import Dict, Type

try:
    from aigov_ep.targets import TARGETS as EP_TARGETS
    from aigov_ep.targets import get_target as ep_get_target

    try:
        from aigov_ep.targets.base import TargetAdapter as EpTargetAdapter
    except ImportError:
        pass
    else:
        TargetAdapter = EpTargetAdapter

    TARGETS = EP_TARGETS
    get_target = ep_get_target
except ImportError:
    from .base import TargetAdapter
    from .http_target import HttpTargetAdapter
    from .mock_llm import MockTargetAdapter
    from .scripted import ScriptedMockTargetAdapter

    TARGETS: Dict[str, Type[TargetAdapter]] = {
        HttpTargetAdapter.name: HttpTargetAdapter,
        MockTargetAdapter.name: MockTargetAdapter,
        ScriptedMockTargetAdapter.name: ScriptedMockTargetAdapter,
    }

    def get_target(name: str) -> Type[TargetAdapter]:
        if name not in TARGETS:
            raise KeyError(f"Unknown target adapter: {name}")
        return TARGETS[name]
