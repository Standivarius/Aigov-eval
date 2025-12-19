"""Environment bootstrap using python-dotenv."""

from __future__ import annotations

from typing import Dict, List, Optional

try:
    from dotenv import dotenv_values, find_dotenv, load_dotenv
except Exception:  # pragma: no cover - optional dependency
    dotenv_values = None
    find_dotenv = None
    load_dotenv = None


_BOOTSTRAPPED = False
_STATE: Dict[str, Optional[object]] = {}


def init_env(debug: bool = False) -> Dict[str, Optional[object]]:
    global _BOOTSTRAPPED, _STATE
    if _BOOTSTRAPPED:
        if debug:
            _debug_print(_STATE)
        return _STATE

    if find_dotenv is None or load_dotenv is None or dotenv_values is None:
        print(
            "python-dotenv not installed; skipping .env loading "
            "(install python-dotenv to enable .env support)."
        )
        _STATE = {
            "dotenv_path": None,
            "found": False,
            "loaded_keys": [],
        }
        _BOOTSTRAPPED = True
        return _STATE

    env_path = find_dotenv()
    found = bool(env_path)
    loaded_keys: List[str] = []

    if found:
        values = dotenv_values(env_path)
        loaded_keys = sorted([key for key in values.keys() if key])
        load_dotenv(dotenv_path=env_path, override=False)

    _STATE = {
        "dotenv_path": env_path or None,
        "found": found,
        "loaded_keys": loaded_keys,
    }
    _BOOTSTRAPPED = True

    if debug:
        _debug_print(_STATE)
    return _STATE


def _debug_print(state: Dict[str, Optional[object]]) -> None:
    found = state.get("found")
    path = state.get("dotenv_path") or "none"
    keys = state.get("loaded_keys") or []
    print(f"[DEBUG] .env found: {found} (path={path})")
    if keys:
        print(f"[DEBUG] .env keys: {', '.join(keys)}")
    else:
        print("[DEBUG] .env keys: none")
