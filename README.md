# FEMA NFIP Intelligent Triage & Map Modernization Assistant

An end-to-end prototype built for the **FEMA Innovation Branch**, demonstrating how low-code platforms (e.g., Power Platform, DHSChat, Gemini Enterprise Agent Designer) pair with Python microservices to automate National Flood Insurance Program (NFIP) underwriting triage, map modernization verification, and Human-in-the-Loop (HITL) workflows.

---

## Key Highlights

- **Automated Geospatial Validation**: Queries the live FEMA National Flood Hazard Layer (NFHL) ArcGIS REST API to verify flood zones in real-time.
- **Deterministic Business Rules Engine**: Calculates elevation margins (Lowest Adjacent Grade vs. Base Flood Elevation) and flags repetitive loss candidates.
- **Agentic Assessment & Governance**: Synthesizes findings into a standardized underwriter memo, enforcing strict **Human-in-the-Loop (HITL)** controls in accordance with federal Responsible AI guidelines (**OMB M-25-21**).

---

## Architectural Flow

```text
[ Citizen / Agent Application ]
              │
              ▼
    [ Low-Code Form / API ]
              │
              ├──────────► [ FEMA NFHL ArcGIS REST API ] ──► (Zone AE, VE, X)
              │
              ▼
   [ Underwriting Rules Engine ] ──► Computes Elevation Differential & Claims
              │
              ▼
   [ AI Triage Memo Agent ]
              │
      ┌───────┴───────────────────┐
      ▼                           ▼
[ Tier 1: Auto-Bind ]    [ Tier 2/3: Mandatory HITL Underwriter Queue ]
```

---

## Rapid Local Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/YOUR_USERNAME/fema-nfip-innovation-demo.git
   cd fema-nfip-innovation-demo
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Run automated test suite:**
   ```bash
   pytest tests/
   ```

4. **Launch Streamlit Web App:**
   ```bash
   streamlit run app.py
   ```

---

## Deployment to Streamlit Cloud (Free & Instant)

1. Push this repository to GitHub.
2. Sign in to [Streamlit Community Cloud](https://share.streamlit.io/).
3. Click **New app**, select this repository and `app.py`, and click **Deploy**.
4. You will receive a permanent, public HTTPS link (e.g., `https://share.streamlit.io/YOUR_USERNAME/fema-nfip-innovation-demo`) ready to submit with your application.
