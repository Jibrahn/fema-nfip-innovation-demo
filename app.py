import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
from typing import Dict, Any, Tuple
import folium
from streamlit_folium import st_folium

st.set_page_config(
    page_title="FEMA NFIP - Intelligent Triage & Map Assistant",
    page_icon="🌊",
    layout="wide"
)

# -----------------------------------------------------------------------------
# SESSION STATE INITIALIZATION
# -----------------------------------------------------------------------------
if "audit_log" not in st.session_state:
    st.session_state.audit_log = []
if "marker_lat" not in st.session_state:
    st.session_state.marker_lat = 30.2460
if "marker_lon" not in st.session_state:
    st.session_state.marker_lon = -87.7000
if "target_address" not in st.session_state:
    st.session_state.target_address = "124 Ocean Breeze Way, Gulf Shores, AL"
if "last_triage_result" not in st.session_state:
    st.session_state.last_triage_result = None

# -----------------------------------------------------------------------------
# GEOCODING & FEMA NFHL GIS QUERY ENGINE
# -----------------------------------------------------------------------------
def geocode_address(address_str: str) -> Tuple[float, float]:
    """Geocodes text address to lat/lon using public Nominatim endpoint."""
    try:
        url = "https://nominatim.openstreetmap.org/search"
        headers = {"User-Agent": "FEMA-Innovation-Prototype/1.0"}
        params = {"q": address_str, "format": "json", "limit": 1}
        resp = requests.get(url, params=params, headers=headers, timeout=4)
        if resp.status_code == 200 and resp.json():
            data = resp.json()[0]
            return float(data["lat"]), float(data["lon"])
    except Exception:
        pass
    return st.session_state.marker_lat, st.session_state.marker_lon

def query_fema_nfhl(lat: float, lon: float) -> Tuple[str, str, Dict[str, Any]]:
    """Queries FEMA NFHL ArcGIS REST API (Layer 28: Flood Hazard Zones)."""
    url = "https://hazards.fema.gov/gis/nfhl/rest/services/public/NFHL/MapServer/28/query"
    params = {
        "geometry": f"{lon},{lat}",
        "geometryType": "esriGeometryPoint",
        "spatialRel": "esriSpatialRelIntersects",
        "outFields": "FLD_ZONE,ZONE_SUBTY,SFHA_TF",
        "returnGeometry": "false",
        "f": "json"
    }
    try:
        resp = requests.get(url, params=params, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data.get("features"):
                attr = data["features"][0].get("attributes", {})
                zone = attr.get("FLD_ZONE", "X")
                subtype = attr.get("ZONE_SUBTY", "Area of Minimal Flood Hazard")
                return zone, subtype, data
        return "X", "Standard / Area of Minimal Flood Hazard", {"status": "default_fallback"}
    except Exception as e:
        return "AE", "1% Annual Chance Flood Hazard (Offline Simulation)", {"error": str(e)}

# -----------------------------------------------------------------------------
# DETERMINISTIC UNDERWRITING RULES ENGINE
# -----------------------------------------------------------------------------
def evaluate_underwriting(zone: str, bfe: float, lag: float, claims: int, foundation: str, occupancy: str) -> Dict[str, Any]:
    elev_diff = lag - bfe
    flags = []
    
    sfha_zones = ["A", "AE", "AH", "AO", "AR", "A99", "V", "VE"]
    is_sfha = any(zone.upper().startswith(z) for z in sfha_zones)
    
    if is_sfha:
        flags.append(f"Structure located in Special Flood Hazard Area (SFHA Zone {zone})")
        
    if elev_diff < 0:
        flags.append(f"Sub-grade exposure: Lowest Grade is {abs(elev_diff):.2f} ft below BFE (Negative Freeboard)")
        
    if foundation in ["Full Basement", "Enclosure (Sub-grade crawlspace)"] and is_sfha:
        flags.append(f"High-consequence foundation risk: {foundation} in SFHA")
        
    if claims >= 2:
        flags.append(f"Severe Repetitive Loss (SRL) candidate: {claims} historic claims recorded")
    elif claims == 1:
        flags.append("Single loss history recorded on parcel")

    if claims >= 2 or elev_diff < -2.0 or (is_sfha and "Basement" in foundation):
        tier = "Tier 3: Mandatory Senior Underwriter Review (HITL Exception)"
        status = "REQUIRES_SENIOR_REVIEW"
        color = "red"
    elif is_sfha or elev_diff < 0 or claims == 1:
        tier = "Tier 2: Standard Underwriter Verification"
        status = "PENDING_VERIFICATION"
        color = "orange"
    else:
        tier = "Tier 1: Accelerated Straight-Through Auto-Bind"
        status = "ELIGIBLE_FOR_AUTO_BIND"
        color = "green"
        
    return {
        "is_sfha": is_sfha,
        "elevation_diff": round(elev_diff, 2),
        "flags": flags,
        "tier": tier,
        "status": status,
        "color": color
    }

# -----------------------------------------------------------------------------
# AGENTIC MEMO SYNTHESIZER
# -----------------------------------------------------------------------------
def generate_agentic_memo(app_id: str, address: str, zone: str, subtype: str, rules: Dict[str, Any], foundation: str, occupancy: str) -> str:
    flag_list = "\n".join([f"  - ⚠️ **{f}**" for f in rules["flags"]]) if rules["flags"] else "  - ✅ No adverse risk indicators found."
    
    actionable_recs = []
    if rules["status"] == "ELIGIBLE_FOR_AUTO_BIND":
        actionable_recs.append("Straight-Through Processing: Issue Standard Flood Insurance Policy (SFIP) policy binder.")
    elif rules["status"] == "PENDING_VERIFICATION":
        actionable_recs.append("Verify building photos and Elevation Certificate Section C2 (Finished Construction).")
        actionable_recs.append("Confirm flood proofing or hydrostatic flood vents for foundation enclosure.")
    else:
        actionable_recs.append("Freeze automated binder: Route parcel to FEMA Regional Specialty Underwriting Unit.")
        actionable_recs.append("Initiate repetitive loss mitigation counseling protocol.")

    rec_list = "\n".join([f"  1. {r}" for r in actionable_recs])

    return f"""### 📋 NFIP Underwriting Triage Memo
**Application Reference:** `{app_id}`  
**Insured Property:** {address}  
**Structure Profile:** {occupancy} | Foundation: {foundation}  
**Flood Zone Classification:** **{zone}** ({subtype}) — *{'SFHA Mandatory Purchase' if rules['is_sfha'] else 'Non-Special Flood Hazard Area'}*

---
#### 1. Technical Risk & Elevation Analysis
- **Elevation Differential ($LAG - BFE$):** `{rules['elevation_diff']} ft`
{flag_list}

#### 2. Agentic Routing & Next Best Actions
- **Triage Result:** **{rules['status']}**
- **Assigned Operational Track:** `{rules['tier']}`
- **Prescribed Operational Steps:**
{rec_list}

---
> 🔒 **Responsible AI / Human-in-the-Loop Governance (OMB M-25-21):**  
> *This decision-support memo was synthesized automatically. Straight-through binding is only authorized for Tier 1. All Tier 2/3 decisions require explicit sign-off from an authorized human underwriter.*
"""

# -----------------------------------------------------------------------------
# STREAMLIT UI
# -----------------------------------------------------------------------------
st.title("🌊 FEMA NFIP - Intelligent Triage & Map Modernization Assistant")
st.caption("FEMA Innovation Branch Technical Prototype | Low-Code / Pro-Code Hybrid Decision Support")

tab_ops, tab_connectors, tab_governance = st.tabs(["🚀 Underwriting Triage Workbench", "🔌 Power Platform / API Payload", "📜 Responsible AI Audit Log"])

with tab_ops:
    col_input, col_results = st.columns([1, 1])

    with col_input:
        st.subheader("1. Property Geospatial & Building Intake")
        
        # Address & Geocode Search
        search_addr = st.text_input("Property Address:", value=st.session_state.target_address)
        if st.button("📍 Geocode & Center Address"):
            new_lat, new_lon = geocode_address(search_addr)
            st.session_state.marker_lat = new_lat
            st.session_state.marker_lon = new_lon
            st.session_state.target_address = search_addr
            st.rerun()

        # Map display with styled hover tooltip
        m = folium.Map(location=[st.session_state.marker_lat, st.session_state.marker_lon], zoom_start=15)
        
        tooltip_html = f"""
        <div style="
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            font-size: 12px;
            line-height: 1.4;
            max-width: 240px;
            padding: 4px;
            white-space: normal;
            word-wrap: break-word;
            overflow-wrap: break-word;
        ">
            <span style="font-weight: 700; color: #0b5394; display: block; margin-bottom: 4px;">Target Property</span>
            <span style="font-weight: 600; color: #222;">Address:</span> {st.session_state.target_address}<br/>
            <span style="font-weight: 600; color: #222;">Coordinates:</span> {st.session_state.marker_lat:.4f}, {st.session_state.marker_lon:.4f}
        </div>
        """
        
        folium.Marker(
            [st.session_state.marker_lat, st.session_state.marker_lon],
            tooltip=folium.Tooltip(tooltip_html, sticky=True),
            icon=folium.Icon(color="red", icon="home", prefix="fa")
        ).add_to(m)
        
        st_folium(
            m,
            height=280,
            use_container_width=True,
            returned_objects=[]
        )

        c_lat, c_lon = st.columns(2)
        manual_lat = c_lat.number_input("Target Latitude", value=st.session_state.marker_lat, format="%.4f")
        manual_lon = c_lon.number_input("Target Longitude", value=st.session_state.marker_lon, format="%.4f")
        
        if manual_lat != st.session_state.marker_lat or manual_lon != st.session_state.marker_lon:
            st.session_state.marker_lat = manual_lat
            st.session_state.marker_lon = manual_lon

        st.markdown("#### Building & Elevation Certificate Details")
        c1, c2 = st.columns(2)
        bfe = c1.number_input("Base Flood Elevation (BFE ft)", value=14.0, step=0.5)
        lag = c2.number_input("Lowest Adjacent Grade (LAG ft)", value=12.5, step=0.5)

        c3, c4 = st.columns(2)
        foundation = c3.selectbox("Foundation Type", ["Slab on Grade", "Crawlspace (Elevated)", "Full Basement", "Enclosure (Sub-grade crawlspace)", "Piles / Stilts"])
        occupancy = c4.selectbox("Occupancy Category", ["Single Family", "2-4 Family", "Commercial / Other Non-Residential", "Manufactured Home"])

        claims = st.number_input("Historic Prior Claims Count", min_value=0, max_value=20, value=1)

        run_btn = st.button("Run Automated Underwriting Triage", type="primary", use_container_width=True)

    with col_results:
        st.subheader("2. Real-Time Triage & Agent Memo")
        
        if run_btn:
            with st.spinner("Calling FEMA NFHL REST Layer 28 & evaluating business rules..."):
                zone, subtype, raw_gis = query_fema_nfhl(st.session_state.marker_lat, st.session_state.marker_lon)
                rules = evaluate_underwriting(zone, bfe, lag, claims, foundation, occupancy)
                memo = generate_agentic_memo("NFIP-APP-2026-8842", search_addr, zone, subtype, rules, foundation, occupancy)
                
                st.session_state.last_triage_result = {
                    "app_id": "NFIP-APP-2026-8842",
                    "address": search_addr,
                    "zone": zone,
                    "subtype": subtype,
                    "rules": rules,
                    "memo": memo,
                    "metrics": {
                        "bfe": bfe,
                        "lag": lag,
                        "diff": rules["elevation_diff"],
                        "foundation": foundation,
                        "occupancy": occupancy,
                        "claims": claims
                    }
                }

        if st.session_state.last_triage_result:
            res = st.session_state.last_triage_result
            rules = res["rules"]
            
            if rules["color"] == "red":
                st.error(f"**Operational Decision:** {rules['tier']}")
            elif rules["color"] == "orange":
                st.warning(f"**Operational Decision:** {rules['tier']}")
            else:
                st.success(f"**Operational Decision:** {rules['tier']}")

            st.markdown(res["memo"])

            st.markdown("---")
            st.subheader("3. Underwriter Human-in-the-Loop (HITL) Sign-off")
            notes = st.text_area("Underwriter Justification & Review Notes:", placeholder="Document verification of Elevation Certificate, surveyor notes, or mitigation...")
            
            a1, a2 = st.columns(2)
            with a1:
                if st.button("✅ Authorize & Bind Policy", use_container_width=True):
                    new_entry = {
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "App_ID": res["app_id"],
                        "Property_Address": res["address"],
                        "Flood_Zone": res["zone"],
                        "Elevation_Diff_ft": res["metrics"]["diff"],
                        "Action_Taken": "AUTHORIZED_BIND",
                        "Officer_Notes": notes if notes.strip() else "Standard auto-bind criteria approved by underwriter.",
                        "OMB_Governance_Status": "Compliant (HITL Verified)"
                    }
                    st.session_state.audit_log.insert(0, new_entry)
                    st.success("✅ Policy successfully bound and appended to the Responsible AI Audit Log!")
            with a2:
                if st.button("🛑 Escalate to Regional Engineer", use_container_width=True):
                    new_entry = {
                        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        "App_ID": res["app_id"],
                        "Property_Address": res["address"],
                        "Flood_Zone": res["zone"],
                        "Elevation_Diff_ft": res["metrics"]["diff"],
                        "Action_Taken": "ESCALATED_FIELD_SURVEY",
                        "Officer_Notes": notes if notes.strip() else "Discrepancy flagged between elevation certificate and NFHL map.",
                        "OMB_Governance_Status": "Compliant (HITL Exception Routed)"
                    }
                    st.session_state.audit_log.insert(0, new_entry)
                    st.warning("⚠️ Application escalated to Regional Engineering Survey. Appended to Audit Log!")
        else:
            st.info("Enter an address or coordinate set on the left, then click **Run Automated Underwriting Triage** to evaluate.")

with tab_connectors:
    st.subheader("Power Platform & Enterprise Low-Code Hand-Off")
    st.markdown("""
    This microservice directly fulfills the job requirement to **support workflow logic, automation, and technical hand-off materials for engineering teams**.
    Below is the normalized JSON schema exported by this prototype to trigger flows in **Microsoft Power Automate**, **DHSChat**, or a **GCP Cloud Function**:
    """)
    current_res = st.session_state.last_triage_result
    connector_payload = {
        "event_type": "NFIP_AUTOMATED_TRIAGE_COMPLETE",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "applicant_metadata": {
            "address": st.session_state.target_address,
            "coordinates": {"lat": st.session_state.marker_lat, "lon": st.session_state.marker_lon}
        },
        "geospatial_verification": {
            "nfhl_endpoint": "https://hazards.fema.gov/gis/nfhl/rest/services/public/NFHL/MapServer/28",
            "detected_zone": current_res["zone"] if current_res else "AE",
            "sfha_status": current_res["rules"]["is_sfha"] if current_res else True
        },
        "underwriting_metrics": current_res["metrics"] if current_res else {
            "bfe_ft": 14.0, "lag_ft": 12.5, "diff": -1.5, "foundation": "Full Basement", "claims": 1
        },
        "governance_compliance": {
            "framework": "OMB M-25-21 Responsible AI",
            "hitl_required": True if not current_res or current_res["rules"]["status"] != "ELIGIBLE_FOR_AUTO_BIND" else False
        }
    }
    st.code(json.dumps(connector_payload, indent=2), language="json")

with tab_governance:
    st.subheader("Responsible AI & Human-in-the-Loop Audit Log")
    st.markdown("""
    Pursuant to **OMB M-25-21** and federal Responsible AI frameworks, all automated determinations and manual underwriter actions 
    are logged below with an immutable timestamp, risk metrics, and officer justification notes:
    """)
    
    if st.session_state.audit_log:
        df_log = pd.DataFrame(st.session_state.audit_log)
        st.dataframe(df_log, use_container_width=True)
        
        csv_data = df_log.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="📥 Download Audit Trail (CSV)",
            data=csv_data,
            file_name=f"nfip_hitl_audit_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
            mime="text/csv"
        )
    else:
        st.info("No underwriter sign-off actions have been executed yet in this session. Complete a review in Tab 1 to see the log update in real-time.")