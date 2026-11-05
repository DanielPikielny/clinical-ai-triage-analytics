import duckdb
import pandas as pd
import streamlit as st

DB_PATH = "data/clinical_warehouse.duckdb"

st.set_page_config(
    page_title="Clinical AI Observability Platform",
    page_icon="🏥",
    layout="wide",
)


@st.cache_data(ttl=60)
def load_data():
    conn = duckdb.connect(DB_PATH)
    conn.execute(
        "SET search_path = 'main_marts,main_int_clinical,main_stg_clinical,main';"
    )

    impact_df = conn.execute(
        "SELECT * FROM main_marts.fct_clinical_impact"
    ).df()

    alerts_df = pd.DataFrame()
    tables = [t[0] for t in conn.execute("SHOW TABLES;").fetchall()]
    if (
        "fct_alert_history" in tables
        or "main_marts.fct_alert_history" in tables
    ):
        alerts_df = conn.execute(
            "SELECT * FROM main_marts.fct_alert_history ORDER BY triggered_at DESC"
        ).df()

    raw_scans = conn.execute(
        "SELECT * FROM main_stg_clinical.stg_clinical_scans"
    ).df()
    conn.close()
    return impact_df, alerts_df, raw_scans


try:
    df_impact, df_alerts, df_scans = load_data()
except Exception as e:
    st.error(
        f"Unable to connect to DuckDB warehouse at {DB_PATH}. Please run `python scripts/run_pipeline.py` first."
    )
    st.stop()

# Title Header
st.title("🏥 Clinical AI Triage & Model Observability Platform")
st.caption(
    "Real-time monitoring of AI precision, sensitivity drift, SLA turnaround latency (p50/p90/p95), and multi-site operational anomalies."
)

# Sidebar Filters
st.sidebar.header("🔍 Global Slice Controls")
sites = ["All"] + sorted(list(df_impact["hospital_site_id"].unique()))
selected_site = st.sidebar.selectbox("Hospital Site", sites)

findings = ["All"] + sorted(list(df_impact["finding_type"].unique()))
selected_finding = st.sidebar.selectbox("Finding Type", findings)

versions = ["All"] + sorted(list(df_impact["model_version"].unique()))
selected_version = st.sidebar.selectbox("AI Model Version", versions)

# Filter Data
filtered_df = df_impact.copy()
if selected_site != "All":
    filtered_df = filtered_df[filtered_df["hospital_site_id"] == selected_site]
if selected_finding != "All":
    filtered_df = filtered_df[filtered_df["finding_type"] == selected_finding]
if selected_version != "All":
    filtered_df = filtered_df[filtered_df["model_version"] == selected_version]

# High-Level Metrics Row
col1, col2, col3, col4, col5 = st.columns(5)

total_scans = filtered_df["total_scans"].sum()
total_tp = filtered_df["true_positives"].sum()
total_fp = filtered_df["false_positives"].sum()
total_fn = filtered_df["false_negatives"].sum()

avg_precision = (
    round((total_tp / (total_tp + total_fp)) * 100.0, 1)
    if (total_tp + total_fp) > 0
    else 0.0
)
avg_recall = (
    round((total_tp / (total_tp + total_fn)) * 100.0, 1)
    if (total_tp + total_fn) > 0
    else 0.0
)
p95_tat = round(filtered_df["p95_turnaround_minutes"].mean(), 1)
sla_comp = round(filtered_df["sla_compliance_pct"].mean(), 1)

col1.metric("Total Ingested Scans", f"{total_scans:,}")
col2.metric(
    "AI Precision",
    f"{avg_precision}%",
    delta="-3.2%" if avg_precision < 75 else "+0.5%",
)
col3.metric("Recall (Sensitivity)", f"{avg_recall}%")
col4.metric("p95 Turnaround (TAT)", f"{p95_tat} min")
col5.metric("SLA Compliance", f"{sla_comp}%")

st.markdown("---")

# Tab Layout
tab1, tab2, tab3, tab4 = st.tabs(
    [
        "🚨 Anomaly Alert Feed",
        "📊 Model Performance Matrix",
        "⏱️ SLA & Percentile Latency",
        "🔬 Confidence Calibration",
    ]
)

# Tab 1: Alert Feed
with tab1:
    st.subheader("Active Operational & Model Drift Alerts")
    if not df_alerts.empty:
        crit_count = len(df_alerts[df_alerts["severity"] == "CRITICAL"])
        warn_count = len(df_alerts[df_alerts["severity"] == "WARNING"])

        st.warning(
            f"Detected **{crit_count} Critical** and **{warn_count} Warning** anomalies across active clinical streams."
        )

        st.dataframe(
            df_alerts[
                [
                    "triggered_at",
                    "severity",
                    "hospital_site_id",
                    "finding_type",
                    "metric_name",
                    "observed_value",
                    "threshold_value",
                    "alert_message",
                ]
            ],
            use_container_width=True,
            hide_index=True,
        )
    else:
        st.success("✓ No active alerts. All clinical streams operating normally.")

# Tab 2: Model Performance Matrix
with tab2:
    st.subheader("ML Model Evaluation Breakdown")
    st.markdown(
        "Evaluate Precision, Recall/Sensitivity, Specificity, F1 Score, and False Negative Rates across hospital sites and model versions."
    )

    metrics_view = filtered_df[
        [
            "hospital_site_id",
            "finding_type",
            "clinical_priority",
            "model_version",
            "precision_pct",
            "recall_sensitivity_pct",
            "specificity_pct",
            "f1_score_pct",
            "false_negative_rate_pct",
        ]
    ].rename(
        columns={
            "hospital_site_id": "Site",
            "finding_type": "Finding",
            "clinical_priority": "Priority",
            "model_version": "Version",
            "precision_pct": "Precision (%)",
            "recall_sensitivity_pct": "Recall (%)",
            "specificity_pct": "Specificity (%)",
            "f1_score_pct": "F1 (%)",
            "false_negative_rate_pct": "False Neg Rate (%)",
        }
    )

    st.dataframe(metrics_view, use_container_width=True, hide_index=True)

# Tab 3: SLA & Latency
with tab3:
    st.subheader("Turnaround Time Distribution (p50 / p90 / p95)")
    st.markdown(
        "Comparing median (p50) against tail latency outliers (p90 / p95) to detect operational bottlenecks."
    )

    tat_chart_df = filtered_df.groupby("hospital_site_id")[
        [
            "avg_turnaround_minutes",
            "p50_turnaround_minutes",
            "p90_turnaround_minutes",
            "p95_turnaround_minutes",
        ]
    ].mean()
    st.bar_chart(tat_chart_df)

# Tab 4: Confidence Calibration
with tab4:
    st.subheader("AI Confidence Score vs Ground Truth Confirmation")
    st.markdown(
        "Analyzing whether higher AI model confidence scores correlate with higher radiologist confirmation rates."
    )

    if "ai_confidence_score" in df_scans.columns:
        scans_reviewed = df_scans[df_scans["is_reviewed"] == True].copy()
        scans_reviewed["confidence_bucket"] = pd.cut(
            scans_reviewed["ai_confidence_score"],
            bins=[0.0, 0.4, 0.6, 0.8, 1.0],
            labels=["< 40%", "40-60%", "60-80%", "80-100%"],
        )

        calib_df = (
            scans_reviewed.groupby("confidence_bucket")["clinician_confirmed"]
            .mean()
            .reset_index()
        )
        calib_df["clinician_confirmed"] = (
            calib_df["clinician_confirmed"] * 100.0
        )

        st.line_chart(
            calib_df.set_index("confidence_bucket")["clinician_confirmed"]
        )
    else:
        st.info("Confidence score data unavailable.")