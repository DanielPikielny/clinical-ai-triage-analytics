import sys
import os
import duckdb
import pandas as pd

# Ensure project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DB_PATH = "data/clinical_warehouse.duckdb"


def analyze_incident_root_cause(alert_hash=None, site=None, finding=None, version=None):
    """Correlates active alerts with model drift, version baseline metrics, and sample evidence."""
    conn = duckdb.connect(DB_PATH)
    conn.execute("SET search_path = 'main_marts,main_int_clinical,main_stg_clinical,main';")

    tables = [t[0] for t in conn.execute("SHOW TABLES;").fetchall()]
    if "fct_alert_history" not in tables:
        conn.close()
        return {"error": "fct_alert_history table does not exist."}

    # 1. Fetch Alert Detail
    if alert_hash:
        alert_df = conn.execute(
            "SELECT * FROM main_marts.fct_alert_history WHERE alert_hash = ?", [alert_hash]
        ).df()
    elif site and finding:
        query = "SELECT * FROM main_marts.fct_alert_history WHERE hospital_site_id = ? AND finding_type = ?"
        params = [site, finding]
        if version:
            query += " AND model_version = ?"
            params.append(version)
        alert_df = conn.execute(query, params).df()
    else:
        # Default to highest severity active alert
        alert_df = conn.execute(
            "SELECT * FROM main_marts.fct_alert_history WHERE status = 'ACTIVE' ORDER BY severity ASC, last_detected_at DESC LIMIT 1"
        ).df()

    if alert_df.empty:
        conn.close()
        return {"status": "NO_INCIDENT_FOUND", "message": "No matching alert found for investigation."}

    alert_row = alert_df.iloc[0].to_dict()
    target_site = alert_row["hospital_site_id"]
    target_finding = alert_row["finding_type"]
    target_version = alert_row["model_version"]

    # 2. Correlate Statistical Model Drift (PSI)
    drift_info = {"psi_score": None, "drift_status": "NO_DATA"}
    if "fct_model_drift" in tables:
        drift_df = conn.execute(
            """
            SELECT psi_score, drift_status, baseline_samples, target_samples
            FROM main_marts.fct_model_drift 
            WHERE hospital_site_id = ? AND finding_type = ? AND model_version = ?
            """,
            [target_site, target_finding, target_version],
        ).df()
        if not drift_df.empty:
            drift_info = drift_df.iloc[0].to_dict()

    # 3. Correlate Performance Mart & Version Metrics
    impact_df = conn.execute(
        """
        SELECT 
            total_scans, total_reviewed_scans, precision_pct, recall_sensitivity_pct,
            p95_turnaround_minutes, sla_compliance_pct
        FROM main_marts.fct_clinical_impact
        WHERE hospital_site_id = ? AND finding_type = ? AND model_version = ?
        """,
        [target_site, target_finding, target_version],
    ).df()

    metrics_summary = impact_df.iloc[0].to_dict() if not impact_df.empty else {}

    # 4. Generate Root Cause Recommendation
    recommendations = []
    psi = drift_info.get("psi_score")
    rec = metrics_summary.get("recall_sensitivity_pct")
    prec = metrics_summary.get("precision_pct")
    p95_tat = metrics_summary.get("p95_turnaround_minutes")

    if psi and psi >= 0.25:
        recommendations.append(
            f"Significant confidence distribution shift detected (PSI: {psi}). "
            f"Input DICOM image features at {target_site} have diverged from baseline training distribution."
        )

    if rec is not None and rec < 75.0:
        recommendations.append(
            f"Recall dropped to {rec}% (Sensitivity critical). Risk of false negatives for {target_finding}. "
            "Recommend temporary secondary manual review protocol."
        )

    if prec is not None and prec < 80.0:
        recommendations.append(
            f"Precision degraded to {prec}%. High false positive rate causing clinician notification fatigue."
        )

    if p95_tat is not None and p95_tat > 120.0:
        recommendations.append(
            f"Tail turnaround latency ({p95_tat} min) exceeding SLA target. Check radiologist queue capacity at {target_site}."
        )

    if not recommendations:
        recommendations.append("Metrics within operational parameters. Continue monitoring slice.")

    conn.close()

    return {
        "status": "INCIDENT_ANALYZED",
        "alert": alert_row,
        "drift": drift_info,
        "metrics": metrics_summary,
        "recommendations": recommendations,
    }


if __name__ == "__main__":
    result = analyze_incident_root_cause()
    print("Incident Root Cause Diagnostic Result:\n")
    if result.get("status") == "INCIDENT_ANALYZED":
        a = result["alert"]
        print(f"Incident: {a['alert_hash']} | {a['severity']} | {a['hospital_site_id']} | {a['finding_type']} ({a['model_version']})")
        print(f"Alert Message: {a['alert_message']}")
        print(f"PSI Score: {result['drift'].get('psi_score')} ({result['drift'].get('drift_status')})")
        print("Recommendations:")
        for r in result["recommendations"]:
            print(f"  - {r}")
    else:
        print(result.get("message", "No active incidents."))