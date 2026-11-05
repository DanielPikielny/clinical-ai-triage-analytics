import os
from datetime import datetime
import duckdb
import yaml

DB_PATH = "data/clinical_warehouse.duckdb"
CONFIG_PATH = "config/alert_rules.yml"


def load_config():
    if not os.path.exists(CONFIG_PATH):
        raise FileNotFoundError(
            f"Alert configuration file not found at {CONFIG_PATH}"
        )
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def init_alert_history_table(conn):
    conn.execute("CREATE SCHEMA IF NOT EXISTS main_marts;")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS main_marts.fct_alert_history (
            alert_id VARCHAR,
            triggered_at TIMESTAMP,
            severity VARCHAR,
            hospital_site_id VARCHAR,
            finding_type VARCHAR,
            clinical_priority VARCHAR,
            metric_name VARCHAR,
            observed_value DOUBLE,
            threshold_value DOUBLE,
            alert_message VARCHAR
        );
    """
    )


def run_alert_engine():
    config = load_config()
    global_rules = config["global_thresholds"]
    tat_targets = config["priority_tat_p95_targets_minutes"]

    conn = duckdb.connect(DB_PATH)

    # Clean search_path without spaces after commas
    conn.execute(
        "SET search_path = 'main_marts,main_int_clinical,main_stg_clinical,main';"
    )

    init_alert_history_table(conn)

    print("Running AI Model & Operational SLA Monitoring Engine...\n")

    query = """
        SELECT 
            hospital_site_id,
            finding_type,
            clinical_priority,
            model_version,
            total_scans,
            total_reviewed_scans,
            precision_pct,
            recall_sensitivity_pct,
            p95_turnaround_minutes,
            sla_compliance_pct
        FROM main_marts.fct_clinical_impact
        WHERE total_reviewed_scans >= 5
    """

    df = conn.execute(query).df()

    alerts = []
    timestamp_str = datetime.now()

    for idx, row in df.iterrows():
        site = row["hospital_site_id"]
        finding = row["finding_type"]
        priority = row["clinical_priority"]
        precision = row["precision_pct"]
        recall = row["recall_sensitivity_pct"]
        p95_tat = row["p95_turnaround_minutes"]
        compliance = row["sla_compliance_pct"]

        # 1. Precision Anomaly Check
        if precision is not None:
            if precision < global_rules["precision_critical"]:
                alerts.append(
                    (
                        f"ALT_{idx:05d}_PREC",
                        timestamp_str,
                        "CRITICAL",
                        site,
                        finding,
                        priority,
                        "AI Precision",
                        precision,
                        global_rules["precision_critical"],
                        f"CRITICAL: Precision dropped to {precision}% for {finding} at {site} (Threshold: {global_rules['precision_critical']}%)",
                    )
                )
            elif precision < global_rules["precision_warning"]:
                alerts.append(
                    (
                        f"ALT_{idx:05d}_PREC",
                        timestamp_str,
                        "WARNING",
                        site,
                        finding,
                        priority,
                        "AI Precision",
                        precision,
                        global_rules["precision_warning"],
                        f"WARNING: Low Precision at {precision}% for {finding} at {site} (Threshold: {global_rules['precision_warning']}%)",
                    )
                )

        # 2. Recall (Sensitivity) Anomaly Check
        if recall is not None:
            if recall < global_rules["recall_critical"]:
                alerts.append(
                    (
                        f"ALT_{idx:05d}_REC",
                        timestamp_str,
                        "CRITICAL",
                        site,
                        finding,
                        priority,
                        "AI Recall",
                        recall,
                        global_rules["recall_critical"],
                        f"CRITICAL: Recall/Sensitivity dropped to {recall}% for {finding} at {site} (Threshold: {global_rules['recall_critical']}%)",
                    )
                )

        # 3. p95 Turnaround Time Spike Check
        target_tat = tat_targets.get(priority, 120)
        if p95_tat is not None and p95_tat > target_tat:
            alerts.append(
                (
                    f"ALT_{idx:05d}_TAT",
                    timestamp_str,
                    "WARNING",
                    site,
                    finding,
                    priority,
                    "p95 Turnaround Time",
                    p95_tat,
                    target_tat,
                    f"WARNING: p95 Turnaround latency ({p95_tat} min) exceeded {priority} SLA ({target_tat} min) at {site}",
                )
            )

    # Summary Display & Audit Log Ingestion
    if alerts:
        print(
            f"🚨 ALERT ENGINE TRIGGERED: {len(alerts)} anomalies detected!\n"
        )
        print(
            f"{'SEVERITY':<10} | {'SITE':<10} | {'METRIC':<20} | {'MESSAGE'}"
        )
        print("-" * 85)
        for a in alerts:
            print(f"{a[2]:<10} | {a[3]:<10} | {a[6]:<20} | {a[9]}")

        # Persist alert logs to DuckDB table main_marts.fct_alert_history
        conn.execute("DELETE FROM main_marts.fct_alert_history;")
        conn.executemany(
            """
            INSERT INTO main_marts.fct_alert_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
            alerts,
        )
        print(
            f"\n✓ Successfully logged {len(alerts)} alerts to main_marts.fct_alert_history."
        )
    else:
        print("✓ All operational metrics within normal parameters.")

    conn.close()


if __name__ == "__main__":
    run_alert_engine()