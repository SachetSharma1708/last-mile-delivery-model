"""
Last-Mile Delivery Cost Modeler (US)

Author: Sachet
"""

import streamlit as st
import pandas as pd
import plotly.graph_objects as go

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from core.cost_model import (
    VanAssumptions, DroneAssumptions,
    estimate_van_cost, estimate_drone_cost, calculate_breakeven
)
from api import routing
from api import ai_advisor


st.set_page_config(page_title="Last-Mile Delivery Cost Modeler", page_icon="🚚", layout="wide")

st.markdown("""
<style>
  .main-title { font-size: 2.2rem; font-weight: 800; color: #0f172a; margin-bottom: 0;}
  .subtitle { color: #64748b; font-size: 0.95rem; margin-top: 0.2rem;}
</style>
""", unsafe_allow_html=True)

st.markdown('<p class="main-title">🚚 Last-Mile Delivery Cost Modeler</p>', unsafe_allow_html=True)
st.markdown('<p class="subtitle">Van vs Drone delivery economics · Real distances + transparent cost model · US edition</p>',
            unsafe_allow_html=True)

st.info(
    "**What's real vs modeled:** "
    "🟢 Distances & drive times are **real** (OpenRouteService API). "
    "🟡 All costs are **modeled estimates** from cited benchmarks — editable below. "
    "🤖 AI advice is **advisory** (NVIDIA NIM). "
    "No public API exposes real per-delivery costs, so this tool estimates them transparently."
)

if "routes_df" not in st.session_state:
    st.session_state.routes_df = None
if "van_assumptions" not in st.session_state:
    st.session_state.van_assumptions = VanAssumptions()
if "drone_assumptions" not in st.session_state:
    st.session_state.drone_assumptions = DroneAssumptions()


with st.sidebar:
    st.header("🔑 API Keys")
    ors_key = st.text_input("OpenRouteService API Key", type="password",
                            value=os.environ.get("ORS_API_KEY", ""),
                            help="Free key: openrouteservice.org/dev/#/signup")
    nvidia_key = st.text_input("NVIDIA NIM API Key", type="password",
                               value=os.environ.get("NVIDIA_API_KEY", ""),
                               help="Free key: build.nvidia.com")

    st.divider()
    st.header("📊 Cost Assumptions")
    st.caption("These are MODELED estimates. Edit freely — the report updates.")

    with st.expander("🚐 Van assumptions", expanded=False):
        v = st.session_state.van_assumptions
        v.base_cost_per_delivery = st.number_input("Base cost/delivery ($)", 1.0, 50.0, v.base_cost_per_delivery, 0.10,
                                                   help="US last-mile avg ~$10.10 (Capgemini)")
        v.labor_share = st.slider("Labor share", 0.0, 1.0, v.labor_share, 0.05,
                                 help="Driver wages — dominant last-mile cost (~55%)")
        v.fuel_price_per_gallon = st.number_input("Fuel price ($/gal)", 1.0, 10.0, v.fuel_price_per_gallon, 0.10)
        v.failed_delivery_rate = st.slider("Failed delivery rate", 0.0, 0.3, v.failed_delivery_rate, 0.01)
        v.terrain_multiplier = st.slider("Terrain multiplier", 0.5, 2.0, v.terrain_multiplier, 0.05,
                                        help="USER ASSUMPTION — no industry-standard figure. 1.0=flat, >1=hilly.")

    with st.expander("🚁 Drone assumptions", expanded=False):
        d = st.session_state.drone_assumptions
        d.drones_per_operator = st.slider("Drones per operator", 1, 50, d.drones_per_operator,
                                         help="THE key cost lever (US DOT). Manna runs ~20:1 and is profitable.")
        d.operator_hourly_wage = st.number_input("Operator wage ($/hr)", 10.0, 80.0, d.operator_hourly_wage, 1.0)
        d.deliveries_per_drone_per_hour = st.number_input("Deliveries/drone/hour", 0.5, 12.0, d.deliveries_per_drone_per_hour, 0.5)
        d.max_payload_lbs = st.number_input("Max payload (lbs)", 1.0, 20.0, d.max_payload_lbs, 0.5, help="Zipline ~4 lbs")
        d.drone_unit_cost = st.number_input("Drone unit cost ($)", 1000.0, 100000.0, d.drone_unit_cost, 1000.0)
        d.infrastructure_per_dock = st.number_input("Dock/site setup ($)", 0.0, 500000.0, d.infrastructure_per_dock, 5000.0)


st.subheader("1️⃣ Enter Your ZIP Codes")
col1, col2 = st.columns(2)
with col1:
    warehouse_zip = st.text_input("Warehouse / hub ZIP", value="75001", help="Your distribution origin")
with col2:
    package_lbs = st.number_input("Typical package weight (lbs)", 0.5, 20.0, 2.0, 0.5)

target_zips_input = st.text_area("Target delivery ZIP codes (comma or newline separated)",
                                 value="75201, 75202, 75203, 75204, 75205", height=100)

colA, colB = st.columns([1, 3])
with colA:
    run = st.button("🚀 Build Report", type="primary", use_container_width=True)


if run:
    if not ors_key:
        st.error("Please add your OpenRouteService API key in the sidebar to pull real distances.")
        st.stop()

    raw = target_zips_input.replace("\n", ",")
    target_zips = [z.strip() for z in raw.split(",") if z.strip()]
    if not target_zips:
        st.error("Please enter at least one target ZIP code.")
        st.stop()

    with st.spinner("Geocoding ZIPs and pulling real route distances..."):
        try:
            origin = routing.geocode_zip(warehouse_zip, ors_key)
            if origin is None:
                st.error(f"Could not geocode warehouse ZIP {warehouse_zip}.")
                st.stop()
        except Exception as e:
            st.error(f"Geocoding error: {e}")
            st.stop()

        rows = []
        progress = st.progress(0)
        for i, z in enumerate(target_zips):
            try:
                dest = routing.geocode_zip(z, ors_key)
                if dest is None:
                    continue
                route = routing.get_route_distance(origin, dest, ors_key)
                drone_dist = routing.straight_line_distance(origin, dest)

                van = estimate_van_cost(route["distance_miles"], st.session_state.van_assumptions)
                drone = estimate_drone_cost(drone_dist, st.session_state.drone_assumptions, package_lbs)

                rows.append({
                    "ZIP": z,
                    "Road mi (van)": route["distance_miles"],
                    "Drive min": route["duration_min"],
                    "Air mi (drone)": drone_dist,
                    "Van $/del": van["total"],
                    "Drone $/del": drone["total"],
                    "Drone feasible": "✅" if drone["feasible"] else "❌ too heavy",
                    "Cheaper": "🚁 Drone" if (drone["feasible"] and drone["total"] < van["total"]) else "🚐 Van",
                    "Savings $/del": round(van["total"] - drone["total"], 2) if drone["feasible"] else None,
                })
            except Exception as e:
                st.warning(f"Skipped ZIP {z}: {e}")
            progress.progress((i + 1) / len(target_zips))
        progress.empty()

        if rows:
            st.session_state.routes_df = pd.DataFrame(rows)
        else:
            st.error("No routes could be computed. Check your ZIPs and API key.")


if st.session_state.routes_df is not None:
    st.divider()
    st.subheader("2️⃣ Your Delivery Cost Report")
    st.caption("📝 This table is **fully editable** — change any value, delete rows, and the summary updates.")

    edited = st.data_editor(st.session_state.routes_df, use_container_width=True,
                            num_rows="dynamic", height=350, key="report_editor")

    if len(edited) > 0:
        drone_wins = (edited["Cheaper"] == "🚁 Drone").sum()
        avg_van = edited["Van $/del"].mean()
        avg_drone = edited["Drone $/del"].mean()

        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Avg Van Cost", f"${avg_van:.2f}")
        m2.metric("Avg Drone Cost", f"${avg_drone:.2f}")
        m3.metric("Drone Wins", f"{drone_wins}/{len(edited)} ZIPs")
        m4.metric("Avg Savings", f"${avg_van - avg_drone:.2f}/del",
                  delta=f"{((avg_van-avg_drone)/avg_van*100):.0f}%" if avg_van else None)

        fig = go.Figure()
        fig.add_trace(go.Bar(x=edited["ZIP"], y=edited["Van $/del"], name="Van", marker_color="#3b82f6"))
        fig.add_trace(go.Bar(x=edited["ZIP"], y=edited["Drone $/del"], name="Drone", marker_color="#10b981"))
        fig.update_layout(title="Van vs Drone Cost per Delivery by ZIP (modeled estimates)",
                          barmode="group", height=400, yaxis_title="$ per delivery")
        st.plotly_chart(fig, use_container_width=True)

    st.divider()
    st.subheader("3️⃣ The Break-Even Insight")
    st.caption("The #1 driver of drone economics isn't distance or fuel — it's **how many drones one operator can supervise** (US DOT).")

    be = calculate_breakeven(st.session_state.van_assumptions, st.session_state.drone_assumptions,
                             distance_miles=5.0, package_lbs=package_lbs)
    sweep_df = pd.DataFrame(be["sweep"])

    fig2 = go.Figure()
    fig2.add_trace(go.Scatter(x=sweep_df["drones_per_operator"], y=sweep_df["drone_cost"],
                              name="Drone cost", line=dict(color="#10b981", width=3)))
    fig2.add_trace(go.Scatter(x=sweep_df["drones_per_operator"], y=sweep_df["van_cost"],
                              name="Van cost (baseline)", line=dict(color="#3b82f6", width=2, dash="dash")))
    if be["breakeven_drones_per_operator"]:
        fig2.add_vline(x=be["breakeven_drones_per_operator"], line_color="#ef4444",
                       annotation_text=f"Break-even: {be['breakeven_drones_per_operator']} drones/operator")
    fig2.update_layout(title="When does drone delivery beat vans?",
                       xaxis_title="Drones supervised per operator", yaxis_title="$ per delivery", height=400)
    st.plotly_chart(fig2, use_container_width=True)

    if be["breakeven_drones_per_operator"]:
        st.success(
            f"💡 **Headline:** At your current assumptions, drone delivery becomes cheaper than vans once "
            f"**one operator can supervise {be['breakeven_drones_per_operator']} drones**. Below that, vans win. "
            f"This is why Manna (≈20:1) is profitable and Amazon (low ratio) wasn't."
        )
    else:
        st.warning("At current assumptions, drones never beat vans even at 50:1. "
                   "Try lowering drone hardware/operator cost or raising van cost.")

    st.divider()
    st.subheader("4️⃣ AI Feasibility Advisor")
    st.caption("🤖 Advisory only. The AI reasons over **qualitative** factors — it does not restate the cost math.")

    if len(edited) > 0:
        zip_choice = st.selectbox("Get advice for which ZIP?", edited["ZIP"].tolist())
        notes = st.text_input("Optional context (e.g. 'dense urban', 'hilly rural', 'noise-sensitive')", value="")
        if st.button("🤖 Get AI Advice"):
            row = edited[edited["ZIP"] == zip_choice].iloc[0]
            summary = {
                "zip": zip_choice,
                "distance_miles": row["Road mi (van)"],
                "van_cost": row["Van $/del"],
                "drone_cost": row["Drone $/del"],
                "package_lbs": package_lbs,
                "payload_ok": row["Drone feasible"] == "✅",
                "notes": notes or "none",
            }
            with st.spinner("Asking the model..."):
                advice = ai_advisor.get_feasibility_advice(summary, nvidia_key)
            st.markdown(f"**Advice for ZIP {zip_choice}:**")
            st.write(advice)

    st.divider()
    csv = edited.to_csv(index=False)
    st.download_button("📥 Download Report (CSV)", csv, file_name="last_mile_report.csv", mime="text/csv")


st.divider()
st.caption("🚚 Last-Mile Delivery Cost Modeler · Real distances (OpenRouteService) + transparent modeled costs "
           "+ NVIDIA NIM advisory · All cost figures are estimates for scenario planning, not ground-truth costs.")
