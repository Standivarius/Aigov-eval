import importlib
import importlib.util

import aigov_eval.targets as targets
from aigov_eval.targets import get_target


def _ep_available() -> bool:
    try:
        return importlib.util.find_spec("aigov_ep.targets") is not None
    except ModuleNotFoundError:
        return False


def _assert_adapter_names(module: object) -> tuple[type, type, type]:
    get_target_fn = module.get_target
    http_cls = get_target_fn("http")
    scripted_cls = get_target_fn("scripted")
    mock_cls = get_target_fn("mock-llm")

    assert http_cls.name == "http"
    assert scripted_cls.name == "scripted"
    assert mock_cls.name == "mock-llm"

    return http_cls, scripted_cls, mock_cls


def test_target_registry_prefers_ep_when_opted_in(monkeypatch) -> None:
    assert get_target is not None

    monkeypatch.delenv("AIGOV_USE_EP_TARGETS", raising=False)
    module = importlib.reload(targets)
    http_cls, scripted_cls, mock_cls = _assert_adapter_names(module)

    assert http_cls.__module__.startswith("aigov_eval.targets")
    assert scripted_cls.__module__.startswith("aigov_eval.targets")
    assert mock_cls.__module__.startswith("aigov_eval.targets")

    monkeypatch.setenv("AIGOV_USE_EP_TARGETS", "1")
    module = importlib.reload(targets)
    http_cls, scripted_cls, mock_cls = _assert_adapter_names(module)

    if _ep_available():
        assert http_cls.__module__.startswith("aigov_ep.targets")
        assert scripted_cls.__module__.startswith("aigov_ep.targets")
        assert mock_cls.__module__.startswith("aigov_ep.targets")
    else:
        assert http_cls.__module__.startswith("aigov_eval.targets")
        assert scripted_cls.__module__.startswith("aigov_eval.targets")
        assert mock_cls.__module__.startswith("aigov_eval.targets")
