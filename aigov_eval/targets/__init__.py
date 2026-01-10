"""DEPRECATED: Target adapters are EP-owned. Canonical implementation lives in aigov-mvp/aigov_ep/targets.
This registry prefers aigov_ep.targets when installed; otherwise falls back to local for CI stability.
To use EP targets in evals, set AIGOV_USE_EP_TARGETS=1."""

from __future__ import annotations

import os
from typing import Dict, Type

use_ep = os.getenv("AIGOV_USE_EP_TARGETS", "").strip() in ("1", "true", "TRUE", "yes", "YES")

if use_ep:
    try:
        from aigov_ep.targets import TARGETS as EP_TARGETS
        from aigov_ep.targets import get_target as ep_get_target

    except ImportError:
        use_ep = False
    else:
        try:
            from aigov_ep.targets.base import TargetAdapter as EpTargetAdapter
        except ImportError:
            pass
        else:
            TargetAdapter = EpTargetAdapter

        TARGETS = EP_TARGETS
        get_target = ep_get_target

if not use_ep:
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
