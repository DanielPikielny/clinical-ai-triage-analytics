import os
from datetime import datetime, timedelta
import duckdb
import numpy as np
import pandas as pd

DB_PATH = "data/clinical_warehouse.duckdb"


def calculate_psi(baseline, target, num_bins=10):
    """Calculates Population Stability Index (PSI) between reference baseline and target distribution."""
    bins = np.linspace(0.0, 1.0, num_bins + 1)

    baseline_counts, _ = np.histogram(baseline, bins=bins)
    target_counts, _ = np.histogram(target, bins=bins)

    eps = 1e-4
    P = (target_counts / len(target)) + eps
    Q = (baseline_counts / len(baseline)) + eps

    P = P / np.sum(P)
    Q = Q / np.sum(Q)

    psi_val = np.sum((P - Q) * np.log(P / Q))
    return float(psi_val)


def run_drift_detection():
    conn = duckdb.connect(DB_PATH)
    conn.execute(
        "SET search_path ="
        " 'main_marts,main_int_clinical,main_stg_clinical,main';"
    )

    print("Running Statistical Model Drift Engine (PSI Analysis)...\n")

    df = conn.execute(
        """
        SELECT 
            event_id,
            hospital_site_id,
            finding_type,
            model_version,
            scan_timestamp,
            ai_confidence_score
        FROM main_stg_clinical.stg_clinical_scans
    """
    ).df()

    if df.empty:
        print("No scan records found for drift analysis.")
        conn.close()
        return

    min_date = df["scan_timestamp"].min()
    mid_date = min_date + timedelta(days=15)

    baseline_df = df[df["scan_timestamp"] <= mid_date]
    target_df = df[df["scan_timestamp"] > mid_date]

    drift_results = []

    # Explicitly group by site, finding, AND model_version to prevent cross-version score mixing
    for (site, finding, version), group in df.groupby(
        ["hospital_site_id", "finding_type", "model_version"]
    ):
        base_scores = baseline_df[
            (baseline_df["hospital_site_id"] == site)
            & (baseline_df["finding_type"] == finding)
            & (baseline_df["model_version"] == version)
        ]["ai_confidence_score"]

        target_scores = target_df[
            (target_df["hospital_site_id"] == site)
            & (target_df["finding_type"] == finding)
            & (target_df["model_version"] == version)
        ]["ai_confidence_score"]

        if len(base_scores) >= 10 and len(target_scores) >= 10:
            psi_score = calculate_psi(base_scores, target_scores)

            if psi_score >= 0.25:
                status = "CRITICAL_DRIFT"
            elif psi_score >= 0.10:
                status = "MODERATE_DRIFT"
            else:
                status = "STABLE"

            drift_results.append(
                (
                    site,
                    finding,
                    version,
                    len(base_scores),
                    len(target_scores),
                    round(psi_score, 4),
                    status,
                    datetime.now(),
                )
            )

    results_df = pd.DataFrame(
        drift_results,
        columns=[
            "hospital_site_id",
            "finding_type",
            "model_version",
            "baseline_samples",
            "target_samples",
            "psi_score",
            "drift_status",
            "evaluated_at",
        ],
    )

    conn.execute("CREATE SCHEMA IF NOT EXISTS main_marts;")
    
    # Check if table schema needs updating to include model_version
    tables = [t[0] for t in conn.execute("SHOW TABLES;").fetchall() if "fct_model_drift" in t[0]]
    if tables:
        cols = [c[0] for c in conn.execute("DESCRIBE main_marts.fct_model_drift;").fetchall()]
        if "model_version" not in cols:
            conn.execute("DROP TABLE main_marts.fct_model_drift;")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS main_marts.fct_model_drift (
            hospital_site_id VARCHAR,
            finding_type VARCHAR,
            model_version VARCHAR,
            baseline_samples INT,
            target_samples INT,
            psi_score DOUBLE,
            drift_status VARCHAR,
            evaluated_at TIMESTAMP
        );
    """
    )
    conn.execute("DELETE FROM main_marts.fct_model_drift;")
    conn.register("df_drift", results_df)
    conn.execute(
        "INSERT INTO main_marts.fct_model_drift SELECT * FROM df_drift;"
    )

    print(f"{'SITE':<10} | {'FINDING':<22} | {'VER':<6} | {'PSI':<8} | {'STATUS'}")
    print("-" * 65)
    for _, r in results_df.sort_values(
        by="psi_score", ascending=False
    ).head(10).iterrows():
        print(
            f"{r['hospital_site_id']:<10} | {r['finding_type']:<22} | {r['model_version']:<6} | {r['psi_score']:<8} | {r['drift_status']}"
        )

    print(
        f"\n✓ Logged {len(results_df)} model-version drift evaluations to main_marts.fct_model_drift."
    )
    conn.close()


if __name__ == "__main__":
    run_drift_detection()