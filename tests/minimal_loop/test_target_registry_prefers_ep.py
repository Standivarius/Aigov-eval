import importlib.util

from aigov_eval.targets import get_target


def test_target_registry_prefers_ep_when_available() -> None:
    http_cls = get_target("http")
    scripted_cls = get_target("scripted")
    mock_cls = get_target("mock-llm")

    try:
        ep_available = importlib.util.find_spec("aigov_ep.targets") is not None
    except ModuleNotFoundError:
        ep_available = False

    assert http_cls.name == "http"
    assert scripted_cls.name == "scripted"
    assert mock_cls.name == "mock-llm"

    if ep_available:
        assert http_cls.__module__.startswith("aigov_ep.targets")
        assert scripted_cls.__module__.startswith("aigov_ep.targets")
        assert mock_cls.__module__.startswith("aigov_ep.targets")
    else:
        assert http_cls.__module__.startswith("aigov_eval.targets")
        assert scripted_cls.__module__.startswith("aigov_eval.targets")
        assert mock_cls.__module__.startswith("aigov_eval.targets")
