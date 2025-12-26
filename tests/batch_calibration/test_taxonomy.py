import glob
import json


def test_calibration_cases_parse_and_have_expected_outcome():
    paths = sorted(glob.glob("cases/calibration/*.json"))
    assert paths, "No calibration cases found"

    for p in paths:
        d = json.load(open(p))
        assert "expected_outcome" in d, f"{p} missing expected_outcome"
        exp = d["expected_outcome"]
        assert "verdict" in exp, f"{p} expected_outcome missing verdict"

        # v2 preferred
        if "required_signals" in exp:
            req = exp.get("required_signals", [])
            allow = exp.get("allowed_extra_signals", [])
            assert isinstance(req, list), f"{p} required_signals not list"
            assert isinstance(allow, list), f"{p} allowed_extra_signals not list"
        else:
            # v1 fallback
            sig = exp.get("signals", [])
            assert isinstance(sig, list), f"{p} signals not list"
