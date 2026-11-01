import duckdb
import pandas as pd
import streamlit as st

# Page Configuration
st.set_page_config(
    page_title="Clinical AI Triage Performance Dashboard",
    page_icon="🏥",
    layout="wide",
)

DB_PATH = "data/clinical_warehouse.duckdb"


@st.cache_data(ttl=60)
def load_data():
    conn = duckdb.connect(DB_PATH)

    # Load Marts & Intermediate Data
    marts_df = conn.execute(
        "SELECT * FROM main_marts.fct_clinical_impact;"
    ).df()
    detail_df = conn.execute(
        "SELECT * FROM main_int_clinical.int_clinical_turnaround;"
    ).df()

    conn.close()
    return marts_df, detail_df


try:
    marts_df, detail_df = load_data()

    st.title("🏥 Clinical AI Triage Operational & Impact Analytics")
    st.markdown(
        "Evaluating AI detection precision, physician turnaround times (TAT), and hospital workflow efficiency."
    )
    st.divider()

    # Sidebar Filters
    st.sidebar.header("Filter Options")
    selected_site = st.sidebar.multiselect(
        "Select Hospital Site(s):",
        options=marts_df["hospital_site_id"].unique(),
        default=marts_df["hospital_site_id"].unique(),
    )

    selected_priority = st.sidebar.multiselect(
        "Select Priority:",
        options=marts_df["clinical_priority"].unique(),
        default=marts_df["clinical_priority"].unique(),
    )

    # Apply Filters
    filtered_marts = marts_df[
        (marts_df["hospital_site_id"].isin(selected_site))
        & (marts_df["clinical_priority"].isin(selected_priority))
    ]

    filtered_detail = detail_df[
        (detail_df["hospital_site_id"].isin(selected_site))
        & (detail_df["clinical_priority"].isin(selected_priority))
    ]

    # Metric KPI Cards
    col1, col2, col3, col4 = st.columns(4)

    total_scans = filtered_marts["total_scans"].sum()
    total_alerts = filtered_marts["total_ai_alerts"].sum()
    total_tp = filtered_marts["true_positives"].sum()

    overall_precision = (
        round((total_tp / total_alerts) * 100, 2) if total_alerts > 0 else 0
    )
    avg_tat = round(filtered_marts["avg_turnaround_minutes"].mean(), 1)

    col1.metric("Total Scans Processed", f"{total_scans:,}")
    col2.metric("AI Flagged Alerts", f"{total_alerts:,}")
    col3.metric("AI Precision Rate", f"{overall_precision}%")
    col4.metric("Avg Turnaround Time", f"{avg_tat} mins")

    st.divider()

    # Charts Section
    left_col, right_col = st.columns(2)

    with left_col:
        st.subheader("AI Precision by Finding Type")
        precision_by_finding = (
            filtered_detail.groupby("finding_type")
            .apply(
                lambda x: round(
                    (
                        (x["ai_detection_classification"] == "TRUE_POSITIVE").sum()
                        / (x["ai_flagged"] == True).sum()  # noqa: E712
                    )
                    * 100,
                    2,
                )
                if (x["ai_flagged"] == True).sum() > 0  # noqa: E712
                else 0
            )
            .reset_index(name="Precision %")
        )

        st.bar_chart(
            precision_by_finding.set_index("finding_type")["Precision %"]
        )

    with right_col:
        st.subheader("Turnaround Performance Distribution")
        tat_dist = filtered_detail[
            "turnaround_performance_category"
        ].value_counts()
        st.bar_chart(tat_dist)

    # Detailed Table View
    st.divider()
    st.subheader("Hospital Aggregated Mart View")
    st.dataframe(filtered_marts, use_container_width=True)

except Exception as e:
    st.error(f"Error loading dashboard data: {e}")
    st.info("Ensure DuckDB database exists and dbt models have run.")