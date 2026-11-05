import pytest
from app import evaluate_underwriting

# -----------------------------------------------------------------------------
# 1. TIER 1: ACCELERATED AUTO-BIND TESTS
# -----------------------------------------------------------------------------
def test_tier1_auto_bind():
    """Zone X with positive freeboard and 0 claims should qualify for auto-bind."""
    res = evaluate_underwriting(
        zone="X",
        bfe=0.0,
        lag=5.0,
        claims=0,
        foundation="Slab on Grade",
        occupancy="Single Family"
    )
    assert res["status"] == "ELIGIBLE_FOR_AUTO_BIND"
    assert res["color"] == "green"
    assert len(res["flags"]) == 0

# -----------------------------------------------------------------------------
# 2. TIER 2: STANDARD UNDERWRITER VERIFICATION TESTS
# -----------------------------------------------------------------------------
def test_tier2_sfha_standard():
    """SFHA Zone AE with positive grade requires standard underwriter verification."""
    res = evaluate_underwriting(
        zone="AE",
        bfe=10.0,
        lag=12.0,
        claims=0,
        foundation="Slab on Grade",
        occupancy="Single Family"
    )
    assert res["status"] == "PENDING_VERIFICATION"
    assert res["color"] == "orange"
    assert any("Special Flood Hazard Area" in f for f in res["flags"])

def test_tier2_single_claim():
    """A single prior loss triggers standard manual verification."""
    res = evaluate_underwriting(
        zone="X",
        bfe=0.0,
        lag=5.0,
        claims=1,
        foundation="Slab on Grade",
        occupancy="Single Family"
    )
    assert res["status"] == "PENDING_VERIFICATION"
    assert any("Single loss history" in f for f in res["flags"])

# -----------------------------------------------------------------------------
# 3. TIER 3: MANDATORY SENIOR REVIEW (HITL EXCEPTION) TESTS
# -----------------------------------------------------------------------------
def test_tier3_repetitive_loss():
    """Two or more prior claims must route to Tier 3 Senior Review."""
    res = evaluate_underwriting(
        zone="AE",
        bfe=10.0,
        lag=12.0,
        claims=2,
        foundation="Slab on Grade",
        occupancy="Single Family"
    )
    assert res["status"] == "REQUIRES_SENIOR_REVIEW"
    assert res["color"] == "red"
    assert any("Severe Repetitive Loss" in f for f in res["flags"])

def test_tier3_subgrade_deficit():
    """Grade more than 2 feet below BFE is a severe sub-grade exposure."""
    res = evaluate_underwriting(
        zone="AE",
        bfe=15.0,
        lag=12.5,
        claims=0,
        foundation="Slab on Grade",
        occupancy="Single Family"
    )
    assert res["status"] == "REQUIRES_SENIOR_REVIEW"
    assert res["color"] == "red"
    assert res["elevation_diff"] == -2.5

def test_tier3_basement_in_sfha():
    """A Full Basement inside an SFHA zone must trigger Tier 3 senior review."""
    res = evaluate_underwriting(
        zone="AE",
        bfe=12.0,
        lag=14.0,
        claims=0,
        foundation="Full Basement",
        occupancy="Single Family"
    )
    assert res["status"] == "REQUIRES_SENIOR_REVIEW"
    assert res["color"] == "red"
    assert any("Basement in SFHA" in f for f in res["flags"])

# -----------------------------------------------------------------------------
# 4. BOUNDARY TESTS
# -----------------------------------------------------------------------------
def test_zero_elevation_boundary():
    """LAG exactly equal to BFE (0.0 ft elevation difference)."""
    res = evaluate_underwriting(
        zone="AE",
        bfe=10.0,
        lag=10.0,
        claims=0,
        foundation="Slab on Grade",
        occupancy="Single Family"
    )
    assert res["elevation_diff"] == 0.0
    assert not any("Sub-grade exposure" in f for f in res["flags"])