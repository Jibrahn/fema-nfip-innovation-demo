import pytest
from app import evaluate_underwriting

def test_tier1_auto_bind():
    # Zone X, positive elevation, 0 claims
    res = evaluate_underwriting(zone="X", bfe=0.0, lag=5.0, claims=0)
    assert res["status"] == "ELIGIBLE_FOR_AUTO_BIND"
    assert len(res["flags"]) == 0

def test_tier3_repetitive_loss():
    # Zone AE, 2 prior claims
    res = evaluate_underwriting(zone="AE", bfe=10.0, lag=12.0, claims=2)
    assert res["status"] == "REQUIRES_MANUAL_REVIEW"
    assert any("Repetitive Loss" in f for f in res["flags"])

def test_tier3_subgrade():
    # Zone AE, Grade 3 ft below BFE
    res = evaluate_underwriting(zone="AE", bfe=15.0, lag=12.0, claims=0)
    assert res["status"] == "REQUIRES_MANUAL_REVIEW"
    assert any("Sub-grade" in f for f in res["flags"])
