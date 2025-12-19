import os

import pytest


E2E_ENABLED = os.getenv("AIGOV_E2E") == "1"


@pytest.mark.skipif(not E2E_ENABLED, reason="Set AIGOV_E2E=1 to run TargetLab E2E tests")
def test_targetlab_contract_smoke():
    assert E2E_ENABLED
