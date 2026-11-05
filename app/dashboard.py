import duckdb
import numpy as np
import pandas as pd
import streamlit as st

DB_PATH = "data/clinical_warehouse.duckdb"

st.set_page_config(page_title="Clinical AI Observability Platform", page_icon="🏥", layout="wide")


@st.cache_data(ttl=60)
def load_data():
    conn = duckdb.connect(DB_PATH)
    conn.execute("SET search_path = 'main_marts,main_int_clinical,main_stg_clinical,main';")

    impact_df = conn.execute("SELECT * FROM main_marts.fct_clinical_impact").df()
    
    alerts_df = pd.DataFrame()
    drift_df = pd.DataFrame()
    tables = [t[0] for t in conn.execute("SHOW TABLES;").fetchall()]
    
    if "fct_alert_history" in tables or "main_marts.fct_alert_history" in tables:
        alerts_df = conn.execute("SELECT * FROM main_marts.fct_alert_history ORDER BY last_detected_at DESC").df()

    if "fct_model_drift" in tables or "main_marts.fct_model_drift" in tables:
        drift_df = conn.execute("SELECT * FROM main_marts.fct_model_drift ORDER BY psi_score DESC").df()

    int_df = conn.execute("SELECT * FROM main_int_clinical.int_clinical_turnaround").df()
    conn.close()
    return impact_df, alerts_df, drift_df, int_df


try:
    df_impact, df_alerts, df_drift, df_int = load_data()
except Exception:
    st.error(f"Unable to connect to DuckDB warehouse at {DB_PATH}. Please run pipeline first.")
    st.stop()

st.title("Clinical AI Triage & Model Observability Platform")
st.caption("Real-time clinical ML monitoring with direct record-level quantiles, persistent alert state, and Population Stability Index (PSI) drift tracking.")

# Global Filters
st.sidebar.header("Global Slice Controls")
sites = ["All"] + sorted(list(df_int["hospital_site_id"].unique()))
selected_site = st.sidebar.selectbox("Hospital Site", sites)

findings = ["All"] + sorted(list(df_int["finding_type"].unique()))
selected_finding = st.sidebar.selectbox("Finding Type", findings)

versions = ["All"] + sorted(list(df_int["model_version"].unique()))
selected_version = st.sidebar.selectbox("AI Model Version", versions)

filtered_int = df_int.copy()
if selected_site != "All":
    filtered_int = filtered_int[filtered_int["hospital_site_id"] == selected_site]
if selected_finding != "All":
    filtered_int = filtered_int[filtered_int["finding_type"] == selected_finding]
if selected_version != "All":
    filtered_int = filtered_int[filtered_int["model_version"] == selected_version]

reviewed_int = filtered_int[filtered_int["is_reviewed"] == True]

total_scans = len(filtered_int)
total_tp = reviewed_int["is_tp"].sum()
total_fp = reviewed_int["is_fp"].sum()
total_fn = reviewed_int["is_fn"].sum()

calc_precision = round((total_tp / (total_tp + total_fp)) * 100.0, 1) if (total_tp + total_fp) > 0 else 0.0
calc_recall = round((total_tp / (total_tp + total_fn)) * 100.0, 1) if (total_tp + total_fn) > 0 else 0.0

p95_tat = round(np.percentile(reviewed_int["total_turnaround_minutes"].dropna(), 95), 1) if len(reviewed_int) > 0 else 0.0
sla_comp = round((reviewed_int["met_sla"].sum() / len(reviewed_int)) * 100.0, 1) if len(reviewed_int) > 0 else 0.0

col1, col2, col3, col4, col5 = st.columns(5)
col1.metric("Total Scans", f"{total_scans:,}")
col2.metric("AI Precision", f"{calc_precision}%")
col3.metric("Recall (Sensitivity)", f"{calc_recall}%")
col4.metric("Record-Level p95 TAT", f"{p95_tat} min")
col5.metric("SLA Compliance", f"{sla_comp}%")

st.markdown("---")

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "Persistent Alerts", 
    "Statistical Model Drift (PSI)", 
    "Model Performance Mart", 
    "Latency Distribution", 
    "Reliability & ECE Calibration"
])

with tab1:
    st.subheader("Persistent Alert Audit Trail")
    if not df_alerts.empty:
        active_alerts = df_alerts[df_alerts["status"] == "ACTIVE"]
        st.warning(f"Currently tracking **{len(active_alerts)} ACTIVE alerts** across monitored streams.")
        st.dataframe(df_alerts[["first_detected_at", "last_detected_at", "status", "severity", "hospital_site_id", "finding_type", "metric_name", "observed_value", "alert_message"]], use_container_width=True, hide_index=True)
    else:
        st.success("✓ No active alerts.")

with tab2:
    st.subheader("Population Stability Index (PSI) Distribution Shift Analysis")
    st.markdown("PSI quantifies confidence distribution shifts between the baseline reference window and the monitoring window (PSI > 0.25 indicates critical drift).")
    if not df_drift.empty:
        st.dataframe(df_drift[["hospital_site_id", "finding_type", "baseline_samples", "target_samples", "psi_score", "drift_status", "evaluated_at"]], use_container_width=True, hide_index=True)
    else:
        st.info("No drift analysis data available.")

with tab3:
    st.subheader("Aggregated Clinical Impact Mart")
    st.dataframe(df_impact, use_container_width=True, hide_index=True)

with tab4:
    st.subheader("Site Turnaround Comparison")
    tat_chart_df = df_impact.groupby("hospital_site_id")[["p50_turnaround_minutes", "p90_turnaround_minutes", "p95_turnaround_minutes"]].mean()
    st.bar_chart(tat_chart_df)

with tab5:
    st.subheader("Model Confidence Reliability Diagram & ECE")
    if "ai_confidence_score" in filtered_int.columns:
        calib_df = reviewed_int.copy()
        calib_df["conf_bin"] = pd.cut(calib_df["ai_confidence_score"], bins=np.linspace(0, 1, 11), include_lowest=True)
        
        rel_chart = calib_df.groupby("conf_bin", observed=False).agg(
            avg_confidence=("ai_confidence_score", "mean"),
            empirical_accuracy=("clinician_confirmed", "mean"),
            count=("event_id", "count")
        ).reset_index()

        total_sample_count = rel_chart["count"].sum()
        ece = ((rel_chart["count"] / total_sample_count) * (rel_chart["avg_confidence"] - rel_chart["empirical_accuracy"]).abs()).sum() * 100.0

        st.metric("Expected Calibration Error (ECE)", f"{round(ece, 2)}%")
        rel_chart["conf_label"] = rel_chart["avg_confidence"].round(2)
        chart_data = rel_chart.set_index("conf_label")[["empirical_accuracy", "avg_confidence"]]
        st.line_chart(chart_data)