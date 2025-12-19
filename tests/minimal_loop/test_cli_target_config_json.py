import pytest

from aigov_eval.cli import _load_target_config


def test_load_target_config_valid_json():
    config = _load_target_config('{"base_url":"http://localhost:8000","chat_path":"/chat"}')
    assert config["base_url"] == "http://localhost:8000"
    assert config["chat_path"] == "/chat"


def test_load_target_config_invalid_json_exits():
    with pytest.raises(SystemExit) as excinfo:
        _load_target_config("{not valid json}")
    assert excinfo.value.code not in (0, None)
    assert "Invalid --target-config-json" in str(excinfo.value)


def test_load_target_config_non_dict_exits():
    with pytest.raises(SystemExit) as excinfo:
        _load_target_config('["not","a","dict"]')
    assert excinfo.value.code not in (0, None)
    assert "expected a JSON object" in str(excinfo.value)
