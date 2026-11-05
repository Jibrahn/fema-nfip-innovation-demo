import pytest
from app import evaluate_underwriting, geocode_address

# -----------------------------------------------------------------------------
# 1. TIER 1: ACCELERATED AUTO-BIND TESTS
# -----------------------------------------------------------------------------
def test_tier1_auto_bind_minimal_hazard():
    """Zone X with positive elevation margin and zero claims qualifies for auto-bind."""
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
    assert res["elevation_diff"] == 5.0


# -----------------------------------------------------------------------------
# 2. TIER 2: STANDARD UNDERWRITER VERIFICATION TESTS
# -----------------------------------------------------------------------------
def test_tier2_sfha_positive_freeboard():
    """SFHA Zone AE with positive freeboard requires standard officer verification."""
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

def test_tier2_single_claim_zone_x():
    """Single historical claim in minimal hazard zone prompts standard verification."""
    res = evaluate_underwriting(
        zone="X",
        bfe=0.0,
        lag=4.0,
        claims=1,
        foundation="Slab on Grade",
        occupancy="Single Family"
    )
    assert res["status"] == "PENDING_VERIFICATION"
    assert any("Single loss history" in f for f in res["flags"])


# -----------------------------------------------------------------------------
# 3. TIER 3: MANDATORY SENIOR UNDERWRITER REVIEW (HITL EXCEPTIONS)
# -----------------------------------------------------------------------------
def test_tier3_severe_repetitive_loss():
    """Two or more historical claims trigger Severe Repetitive Loss senior review."""
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

def test_tier3_severe_subgrade_elevation():
    """Grade more than 2 feet below BFE is a severe sub-grade structural exposure."""
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
    assert any("Sub-grade exposure" in f for f in res["flags"])

def test_tier3_full_basement_in_sfha():
    """Full basement foundation inside an SFHA zone forces mandatory senior review."""
    res = evaluate_underwriting(
        zone="AE",
        bfe=12.0,
        lag=13.0,
        claims=0,
        foundation="Full Basement",
        occupancy="Single Family"
    )
    assert res["status"] == "REQUIRES_SENIOR_REVIEW"
    assert res["color"] == "red"
    assert any("High-consequence foundation risk" in f for f in res["flags"])


# -----------------------------------------------------------------------------
# 4. BOUNDARY & EDGE CASE TESTS
# -----------------------------------------------------------------------------
def test_exact_bfe_match():
    """LAG exactly matching BFE (0.0 ft freeboard) does not flag negative subgrade."""
    res = evaluate_underwriting(
        zone="AE",
        bfe=14.0,
        lag=14.0,
        claims=0,
        foundation="Piles / Stilts",
        occupancy="Single Family"
    )
    assert res["elevation_diff"] == 0.0
    assert not any("Sub-grade exposure" in f for f in res["flags"])


# -----------------------------------------------------------------------------
# 5. GEOSPATIAL ADDRESS ENGINE VALIDATION
# -----------------------------------------------------------------------------
def test_geocode_blank_address_rejection():
    """Blank or whitespace-only queries are safely rejected without API calls."""
    lat, lon, success, msg = geocode_address("")
    assert success is False
    assert "cannot be blank" in msg

def test_geocode_valid_us_address():
    """Valid street address resolves successfully via ArcGIS geocoder."""
    lat, lon, success, msg = geocode_address("1600 Pennsylvania Ave NW, Washington, DC 20500")
    assert success is True
    assert 38.80 <= lat <= 39.00
    assert -77.10 <= lon <= -76.90