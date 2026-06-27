import streamlit as st
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, timedelta

st.set_page_config(
    layout="wide",
    page_title="Supply Chain Intelligence Hub",
    page_icon="📦",
)

# ─── Configuration ────────────────────────────────────────────────────────────
SHEET_ID = "1E5X0bWQ6P3HVHcjTZvsojrR1phu_sGd8f67cbz15RSk"
GID = "1019333533"
CSV_URL = f"https://docs.google.com/spreadsheets/d/{SHEET_ID}/export?format=csv&gid={GID}"

SUPPLIERS = ["MedSource LLC", "PharmaDist UAE", "Gulf Health Supplies", "AlKhaleej Medical"]
CATEGORIES = ["Pharma", "Supplements", "OTC", "PPE", "Hygiene", "Equipment", "Diagnostics"]

# Columns the user is allowed to edit in Scenario Mode
EDITABLE_COLS = [
    "SKU", "Product Name", "Category", "ABC Class",
    "Stock on Hand", "Reorder Point", "Days in Stock",
    "Days to Expiry", "Unit Cost (AED)", "Supplier",
]


# ─── Helpers ─────────────────────────────────────────────────────────────────
def recompute_derived(df: pd.DataFrame) -> pd.DataFrame:
    """Re-derive all computed columns from the raw editable data."""
    df = df.copy()
    df["Days to Expiry"] = df["Days to Expiry"].clip(lower=0).astype(int)
    df["Stock on Hand"] = df["Stock on Hand"].clip(lower=0).astype(int)
    df["Reorder Point"] = df["Reorder Point"].clip(lower=0).astype(int)
    df["Days in Stock"] = df["Days in Stock"].clip(lower=0).astype(int)
    df["Stock Value (AED)"] = (df["Stock on Hand"] * df["Unit Cost (AED)"]).round(2)
    df["Reorder Needed"] = df["Stock on Hand"] < df["Reorder Point"]
    df["Expiry Status"] = df["Days to Expiry"].apply(
        lambda d: "🔴 Critical" if d < 30 else ("🟡 At Risk" if d < 90 else "🟢 Healthy")
    )
    return df


# ─── Sample Data ─────────────────────────────────────────────────────────────
@st.cache_data
def make_sample_data() -> pd.DataFrame:
    rng = np.random.default_rng(42)
    today = datetime(2026, 6, 27)

    catalog = [
        ("SKU-001", "Paracetamol 500mg",       "Pharma",       "A", "MedSource LLC"),
        ("SKU-002", "Amoxicillin 250mg",       "Pharma",       "A", "PharmaDist UAE"),
        ("SKU-003", "Vitamin C 1000mg",        "Supplements",  "B", "Gulf Health Supplies"),
        ("SKU-004", "Ibuprofen 400mg",         "Pharma",       "A", "MedSource LLC"),
        ("SKU-005", "Omega-3 Capsules",        "Supplements",  "B", "Gulf Health Supplies"),
        ("SKU-006", "Zinc Tablets",            "Supplements",  "C", "AlKhaleej Medical"),
        ("SKU-007", "Calcium 600mg",           "Supplements",  "C", "AlKhaleej Medical"),
        ("SKU-008", "Metformin 500mg",         "Pharma",       "B", "PharmaDist UAE"),
        ("SKU-009", "Atorvastatin 20mg",       "Pharma",       "A", "MedSource LLC"),
        ("SKU-010", "Hand Sanitizer 500ml",    "Hygiene",      "B", "Gulf Health Supplies"),
        ("SKU-011", "Face Masks N95",          "PPE",          "C", "AlKhaleej Medical"),
        ("SKU-012", "Gloves Nitrile L",        "PPE",          "C", "AlKhaleej Medical"),
        ("SKU-013", "Antiseptic Cream 50g",    "OTC",          "B", "PharmaDist UAE"),
        ("SKU-014", "Cough Syrup 200ml",       "OTC",          "A", "MedSource LLC"),
        ("SKU-015", "Allergy Tablets 10mg",    "OTC",          "B", "Gulf Health Supplies"),
        ("SKU-016", "Antacid Suspension",      "OTC",          "B", "PharmaDist UAE"),
        ("SKU-017", "Eye Drops 10ml",          "Pharma",       "C", "MedSource LLC"),
        ("SKU-018", "Blood Pressure Monitor",  "Equipment",    "C", "AlKhaleej Medical"),
        ("SKU-019", "Glucose Test Strips",     "Diagnostics",  "A", "Gulf Health Supplies"),
        ("SKU-020", "Surgical Masks Box",      "PPE",          "B", "AlKhaleej Medical"),
    ]

    rows = []
    for sku, name, cat, abc, supplier in catalog:
        stock = int(rng.integers(80, 500))
        reorder = int(rng.integers(50, 180))
        days_in_stock = int(rng.integers(5, 100))
        roll = rng.random()
        if roll < 0.10:
            expiry_days = int(rng.integers(5, 29))
        elif roll < 0.30:
            expiry_days = int(rng.integers(30, 90))
        else:
            expiry_days = int(rng.integers(90, 400))
        unit_cost = round(float(rng.uniform(5, 250)), 2)
        rows.append({
            "SKU": sku,
            "Product Name": name,
            "Category": cat,
            "ABC Class": abc,
            "Stock on Hand": stock,
            "Reorder Point": reorder,
            "Days in Stock": days_in_stock,
            "Expiry Date": (today + timedelta(days=expiry_days)).strftime("%Y-%m-%d"),
            "Days to Expiry": expiry_days,
            "Unit Cost (AED)": unit_cost,
            "Supplier": supplier,
        })

    df = pd.DataFrame(rows)
    return recompute_derived(df[EDITABLE_COLS])


# ─── Quick Scenario Presets ───────────────────────────────────────────────────
def scenario_baseline() -> pd.DataFrame:
    return make_sample_data().copy()


def scenario_expiry_crisis(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Force first 5 SKUs into critical expiry window
    for i, days in enumerate([6, 12, 18, 24, 27]):
        if i < len(out):
            out.iloc[i, out.columns.get_loc("Days to Expiry")] = days
    return out


def scenario_stockout(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Drain A-class and B-class stock well below reorder point
    for idx in out.index:
        if out.at[idx, "ABC Class"] in ("A", "B"):
            out.at[idx, "Stock on Hand"] = max(0, int(out.at[idx, "Reorder Point"] * 0.25))
    return out


def scenario_quarter_end(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    # Push all items into 91-180d aging bucket, inflate stock
    for idx in out.index:
        out.at[idx, "Days in Stock"] = int(100 + (idx % 80))
        out.at[idx, "Stock on Hand"] = int(out.at[idx, "Stock on Hand"] * 1.8)
    return out


def scenario_mixed_crisis(df: pd.DataFrame) -> pd.DataFrame:
    """Combines expiry pressure on A-class + stockouts on B-class."""
    out = df.copy()
    for idx in out.index:
        cls = out.at[idx, "ABC Class"]
        if cls == "A":
            out.at[idx, "Days to Expiry"] = max(5, int(out.at[idx, "Days to Expiry"] * 0.15))
        elif cls == "B":
            out.at[idx, "Stock on Hand"] = max(0, int(out.at[idx, "Reorder Point"] * 0.3))
    return out


@st.cache_data(ttl=60)
def get_data_from_sheet():
    return pd.read_csv(CSV_URL)


def enrich_sheet_data(df: pd.DataFrame) -> pd.DataFrame:
    defaults = {
        "Days to Expiry": 180, "Expiry Status": "🟢 Healthy",
        "ABC Class": "B", "Reorder Needed": False,
        "Days in Stock": 30, "Supplier": "Unknown",
    }
    for col, val in defaults.items():
        if col not in df.columns:
            df[col] = val
    if "Stock Value (AED)" not in df.columns and "Stock on Hand" in df.columns:
        df["Stock Value (AED)"] = df["Stock on Hand"] * 10
    return df


# ─── Sidebar ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Controls")

    service_tier = st.radio(
        "**Service Tier**",
        options=[
            "🥉 Tier 1 — Basic Dashboard",
            "🥈 Tier 2 — Automation",
            "🥇 Tier 3 — Workflow AI",
        ],
        index=0,
        help=(
            "**Tier 1:** Live ERP visibility\n\n"
            "**Tier 2:** + automated alerts, scheduled PDF reports, Teams/email\n\n"
            "**Tier 3:** + replenishment engine, inventory blocks, workflow triggers"
        ),
    )

    st.divider()
    use_demo = st.toggle("Use Demo Data", value=True,
                         help="Toggle off to connect to a live Google Sheet.")

    scenario_mode = False
    if use_demo:
        scenario_mode = st.toggle(
            "🧪 Scenario Editor",
            value=False,
            help="Edit any cell to see its live impact on KPIs and charts.",
        )

    if "Tier 2" in service_tier or "Tier 3" in service_tier:
        st.divider()
        st.markdown("**🔔 Alert Channels**")
        st.checkbox("Microsoft Teams", value=True)
        st.checkbox("Email Reports", value=True)
        st.checkbox("Auto PDF Export", value=False)

    st.divider()
    st.markdown(f"**Last Refresh**  \n`{datetime.now().strftime('%Y-%m-%d %H:%M')}`")
    st.caption("Auto-refreshes every 60 s")


# ─── Load / initialise data ───────────────────────────────────────────────────
if "scenario_df" not in st.session_state:
    st.session_state.scenario_df = make_sample_data().copy()

if use_demo:
    if scenario_mode:
        df_display = None   # will be set after scenario controls
    else:
        df_display = recompute_derived(st.session_state.scenario_df)
        st.info(
            "**Demo Mode** — Toggle 'Use Demo Data' off in the sidebar to connect to a live "
            "Google Sheet. Enable **🧪 Scenario Editor** to edit values and see live KPI impact.",
            icon="ℹ️",
        )
else:
    try:
        raw = get_data_from_sheet()
        df_display = enrich_sheet_data(raw)
        st.success("Live Google Sheet connected.", icon="✅")
    except Exception as exc:
        st.warning(f"Could not reach Google Sheet — showing demo data. ({exc})", icon="⚠️")
        df_display = recompute_derived(st.session_state.scenario_df)
    scenario_mode = False  # editor only available in demo mode


# ─── Scenario Editor ──────────────────────────────────────────────────────────
if scenario_mode:
    st.markdown("## 🧪 Live Scenario Editor")
    st.caption(
        "Edit any cell below and the KPIs, charts, and alerts update instantly. "
        "Use the preset buttons for one-click crisis simulations."
    )

    # ── Quick preset buttons ──
    p1, p2, p3, p4, p5 = st.columns(5)

    if p1.button("🏥 Baseline", use_container_width=True, help="Reset to original sample data"):
        st.session_state.scenario_df = scenario_baseline()

    if p2.button("🔴 Expiry Crisis", use_container_width=True,
                 help="Push 5 SKUs into <30-day expiry window"):
        st.session_state.scenario_df = scenario_expiry_crisis(st.session_state.scenario_df)

    if p3.button("📦 A/B Stockout", use_container_width=True,
                 help="Drain A & B class stock far below reorder points"):
        st.session_state.scenario_df = scenario_stockout(st.session_state.scenario_df)

    if p4.button("📅 Quarter-End Buildup", use_container_width=True,
                 help="Simulate end-of-quarter excess stock with high aging"):
        st.session_state.scenario_df = scenario_quarter_end(st.session_state.scenario_df)

    if p5.button("⚡ Mixed Crisis", use_container_width=True,
                 help="A-class nearing expiry + B-class stockout simultaneously"):
        st.session_state.scenario_df = scenario_mixed_crisis(st.session_state.scenario_df)

    # ── Editable table ──
    edited = st.data_editor(
        st.session_state.scenario_df,
        use_container_width=True,
        num_rows="fixed",
        key="inventory_editor",
        disabled=["SKU", "Product Name"],
        column_config={
            "SKU": st.column_config.TextColumn("SKU", disabled=True),
            "Product Name": st.column_config.TextColumn("Product Name", disabled=True),
            "Category": st.column_config.SelectboxColumn(
                "Category", options=CATEGORIES, required=True
            ),
            "ABC Class": st.column_config.SelectboxColumn(
                "ABC Class",
                options=["A", "B", "C"],
                required=True,
                help="A = Fast Mover · B = Medium · C = Slow Mover",
            ),
            "Stock on Hand": st.column_config.NumberColumn(
                "Stock on Hand", min_value=0, step=1, format="%d"
            ),
            "Reorder Point": st.column_config.NumberColumn(
                "Reorder Point", min_value=0, step=1, format="%d"
            ),
            "Days in Stock": st.column_config.NumberColumn(
                "Days in Stock", min_value=0, step=1, format="%d"
            ),
            "Days to Expiry": st.column_config.NumberColumn(
                "Days to Expiry",
                min_value=0,
                step=1,
                format="%d",
                help="<30 = Critical · 30-90 = At Risk · >90 = Healthy",
            ),
            "Unit Cost (AED)": st.column_config.NumberColumn(
                "Unit Cost (AED)", min_value=0.0, step=0.5, format="%.2f"
            ),
            "Supplier": st.column_config.SelectboxColumn(
                "Supplier", options=SUPPLIERS, required=True
            ),
        },
        column_order=EDITABLE_COLS,
    )

    # Persist edits and recompute derived columns
    st.session_state.scenario_df = edited
    df_display = recompute_derived(edited)

    st.divider()

df = df_display  # single reference used by all sections below


# ─── Header ───────────────────────────────────────────────────────────────────
st.markdown("# 📦 Supply Chain Intelligence Hub")
st.caption("Real-time inventory visibility · Automated alerts · Replenishment engine")

st.divider()

# ─── KPI Tiles ────────────────────────────────────────────────────────────────
st.markdown("## 📊 Executive KPIs")
k1, k2, k3, k4 = st.columns(4)

total_skus = len(df)
total_units = int(df["Stock on Hand"].sum()) if "Stock on Hand" in df.columns else 0
critical_count = int((df["Days to Expiry"] < 30).sum()) if "Days to Expiry" in df.columns else 0
reorder_count = int(df["Reorder Needed"].sum()) if "Reorder Needed" in df.columns else 0

k1.metric("Total SKUs Managed", total_skus)
k2.metric("Total Units in Facility", f"{total_units:,}")
k3.metric(
    "Expiring in < 30 Days",
    critical_count,
    delta=f"{critical_count} need action" if critical_count else "All clear",
    delta_color="inverse",
)
k4.metric(
    "Below Reorder Point",
    reorder_count,
    delta=f"{reorder_count} SKUs" if reorder_count else "All stocked",
    delta_color="inverse",
)

st.divider()

# ─── Charts Row ───────────────────────────────────────────────────────────────
c1, c2 = st.columns([3, 2])

with c1:
    st.markdown("### 📈 Stock on Hand vs Reorder Point")
    if "SKU" in df.columns and "Reorder Point" in df.columns:
        chart_df = df.sort_values("Stock on Hand", ascending=False).head(15)
        fig = go.Figure()
        fig.add_bar(
            x=chart_df["SKU"], y=chart_df["Stock on Hand"],
            name="Stock on Hand", marker_color="#3498db",
        )
        fig.add_bar(
            x=chart_df["SKU"], y=chart_df["Reorder Point"],
            name="Reorder Point", marker_color="#e74c3c", opacity=0.75,
        )
        fig.update_layout(
            barmode="overlay", height=320,
            margin=dict(t=10, b=30),
            legend=dict(orientation="h", y=1.1),
        )
        st.plotly_chart(fig, use_container_width=True)

with c2:
    st.markdown("### 🏷️ ABC Classification")
    if "ABC Class" in df.columns:
        abc_df = df["ABC Class"].value_counts().reset_index()
        abc_df.columns = ["Class", "Count"]
        fig2 = px.pie(
            abc_df, names="Class", values="Count", hole=0.55,
            color="Class",
            color_discrete_map={"A": "#27ae60", "B": "#f39c12", "C": "#e74c3c"},
        )
        fig2.update_traces(textinfo="label+percent", textposition="outside")
        fig2.update_layout(
            height=320, margin=dict(t=10, b=10, l=10, r=10), showlegend=False,
        )
        st.plotly_chart(fig2, use_container_width=True)

st.caption(
    "**ABC Classification:** A = Fast Movers · B = Medium Movers · C = Slow Movers"
)

st.divider()

# ─── Aging & Expiry Row ───────────────────────────────────────────────────────
c3, c4 = st.columns(2)

with c3:
    st.markdown("### ⏳ Inventory Aging Distribution")
    if "Days in Stock" in df.columns:
        df["Aging Bucket"] = pd.cut(
            df["Days in Stock"],
            bins=[0, 30, 60, 90, 180, 10_000],
            labels=["0–30 days", "31–60 days", "61–90 days", "91–180 days", "180+ days"],
        )
        aging = (
            df.groupby("Aging Bucket", observed=True)
            .size()
            .reset_index(name="SKUs")
        )
        fig3 = px.bar(
            aging, x="Aging Bucket", y="SKUs",
            color="Aging Bucket", text="SKUs",
            color_discrete_sequence=["#2ecc71", "#f1c40f", "#e67e22", "#e74c3c", "#8e44ad"],
        )
        fig3.update_traces(textposition="outside")
        fig3.update_layout(
            height=300, margin=dict(t=10, b=30),
            showlegend=False, xaxis_title="", yaxis_title="SKU Count",
        )
        st.plotly_chart(fig3, use_container_width=True)

with c4:
    st.markdown("### 🚨 Expiry Risk — Next 90 Days")
    if "Days to Expiry" in df.columns:
        risk_df = df[df["Days to Expiry"] < 90].sort_values("Days to Expiry")
        if not risk_df.empty:
            show_cols = [
                c for c in
                ["SKU", "Product Name", "Days to Expiry", "Stock on Hand", "Expiry Status"]
                if c in risk_df.columns
            ]
            st.dataframe(risk_df[show_cols], hide_index=True,
                         use_container_width=True, height=300)
        else:
            st.success("No items expiring within 90 days.")

st.divider()

# ─── Tier 2: Automation Engine ────────────────────────────────────────────────
if "Tier 2" in service_tier or "Tier 3" in service_tier:
    st.markdown("## 🤖 Tier 2 — Automation Engine")

    t2a, t2b = st.columns(2)

    with t2a:
        st.markdown("#### 📬 Active Notifications")
        if critical_count:
            st.error(f"⚠️ **{critical_count} SKU(s)** expiring in <30 days — Teams alert queued")
        if reorder_count:
            st.warning(
                f"📦 **{reorder_count} SKU(s)** below reorder point — purchase order draft ready"
            )
        st.info("📄 Weekly PDF report scheduled for **Friday 08:00 GST**")
        st.success("🔄 ERP data auto-synced — last pull 3 minutes ago")

    with t2b:
        st.markdown("#### 📅 Automated Report Schedule")
        schedule = pd.DataFrame({
            "Report": [
                "Inventory Health Summary", "Expiry Risk Alert",
                "Reorder Point Breach", "ABC Classification Review",
            ],
            "Frequency": ["Daily", "Daily", "Real-time", "Weekly"],
            "Channel": ["Teams", "Email", "Teams + Email", "Email PDF"],
            "Status": ["✅ Active", "✅ Active", "✅ Active", "✅ Active"],
        })
        st.dataframe(schedule, hide_index=True, use_container_width=True)

    st.divider()

# ─── Tier 3: Workflow AI ──────────────────────────────────────────────────────
if "Tier 3" in service_tier:
    st.markdown("## ⚡ Tier 3 — Workflow Automation")

    st.markdown("#### 🔄 Replenishment Engine")
    if "Reorder Needed" in df.columns:
        replenish_df = df[df["Reorder Needed"]].copy()

        if not replenish_df.empty:
            replenish_df["Suggested Order Qty"] = (
                (replenish_df["Reorder Point"] * 1.5 - replenish_df["Stock on Hand"])
                .clip(lower=0).astype(int)
            )
            replenish_df["Recommended Action"] = replenish_df.apply(
                lambda r: (
                    "🛑 Block Inventory + Raise GRV"
                    if r.get("Days to Expiry", 999) < 30
                    else "📋 Draft Purchase Order"
                ),
                axis=1,
            )
            show_cols = [
                c for c in [
                    "SKU", "Product Name", "Stock on Hand", "Reorder Point",
                    "Suggested Order Qty", "Supplier", "Recommended Action",
                ]
                if c in replenish_df.columns
            ]
            st.dataframe(replenish_df[show_cols], hide_index=True, use_container_width=True)
            st.caption(
                "🛑 Items expiring in <30 days are auto-blocked and a GRV is raised with the vendor. "
                "Items below reorder point receive a draft PO sent via email or Slack — "
                "client reviews and approves before any submission."
            )
            b1, b2, b3 = st.columns(3)
            b1.button("📧 Send PO Drafts via Email", type="primary", use_container_width=True)
            b2.button("💬 Push to Slack Channel", use_container_width=True)
            b3.button("🛑 Apply Inventory Blocks", use_container_width=True)
        else:
            st.success("✅ All SKUs adequately stocked — no replenishment actions required.")

    st.divider()

    st.markdown("#### 🗺️ Network Optimization Insights")
    insights = pd.DataFrame({
        "Insight": [
            "Relocate C-class SKUs to Zone 3 — free up 12% of prime floor space",
            "Move top 5 A-class SKUs to dispatch-adjacent rack — cut pick time ~8%",
            "3 suppliers responsible for 80% of late deliveries — trigger SLA review",
            "Consider cross-docking for A-class to reduce dwell time by up to 20%",
        ],
        "Category": ["Warehousing", "Warehousing", "Procurement", "Last Mile"],
        "Priority": ["High", "Medium", "High", "Low"],
        "Est. Impact": [
            "12% space saving", "8% pick-time reduction",
            "15% lead-time cut", "20% dwell-time cut",
        ],
    })
    st.dataframe(insights, hide_index=True, use_container_width=True)
    st.divider()

# ─── Full Inventory Feed ───────────────────────────────────────────────────────
with st.expander("📋 Full Inventory Feed", expanded=False):
    st.dataframe(df, use_container_width=True, hide_index=True)

st.caption(
    "Supply Chain Intelligence Hub · Proof of Concept · "
    "Tier 1: Live Dashboard · Tier 2: Automation · Tier 3: Workflow AI"
)
