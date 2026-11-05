import hashlib
import os
from datetime import datetime
import duckdb
import yaml

DB_PATH = "data/clinical_warehouse.duckdb"
CONFIG_PATH = "config/alert_rules.yml"


def load_config():
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def init_alert_history_table(conn):
    conn.execute("CREATE SCHEMA IF NOT EXISTS main_marts;")

    # Check if table exists with old schema (missing alert_hash column)
    tables = [
        t[0]
        for t in conn.execute("SHOW TABLES;").fetchall()
        if "fct_alert_history" in t[0]
    ]
    if tables:
        cols = [
            c[0]
            for c in conn.execute(
                "DESCRIBE main_marts.fct_alert_history;"
            ).fetchall()
        ]
        if "alert_hash" not in cols:
            conn.execute("DROP TABLE main_marts.fct_alert_history;")

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS main_marts.fct_alert_history (
            alert_hash VARCHAR PRIMARY KEY,
            first_detected_at TIMESTAMP,
            last_detected_at TIMESTAMP,
            severity VARCHAR,
            hospital_site_id VARCHAR,
            finding_type VARCHAR,
            clinical_priority VARCHAR,
            metric_name VARCHAR,
            observed_value DOUBLE,
            threshold_value DOUBLE,
            alert_message VARCHAR,
            status VARCHAR
        );
    """
    )


def generate_alert_hash(site, finding, priority, metric_name):
    raw_str = f"{site}_{finding}_{priority}_{metric_name}"
    return hashlib.md5(raw_str.encode()).hexdigest()[:12]


def run_alert_engine():
    config = load_config()
    rules = config["global_thresholds"]
    tat_targets = config["priority_tat_p95_targets_minutes"]
    min_scans = rules.get("min_reviewed_scans", 5)

    conn = duckdb.connect(DB_PATH)
    conn.execute("SET search_path = 'main_marts,main_int_clinical,main_stg_clinical,main';")
    init_alert_history_table(conn)

    print("Running Persistent AI Model & Operational SLA Monitoring Engine...\n")

    query = f"""
        SELECT 
            hospital_site_id,
            finding_type,
            clinical_priority,
            total_reviewed_scans,
            precision_pct,
            recall_sensitivity_pct,
            p95_turnaround_minutes,
            sla_compliance_pct
        FROM main_marts.fct_clinical_impact
        WHERE total_reviewed_scans >= {min_scans}
    """

    df = conn.execute(query).df()
    now_ts = datetime.now()
    active_hashes = set()
    current_alerts = []

    for _, row in df.iterrows():
        site, finding, priority = row["hospital_site_id"], row["finding_type"], row["clinical_priority"]
        prec, rec, p95_tat, comp = row["precision_pct"], row["recall_sensitivity_pct"], row["p95_turnaround_minutes"], row["sla_compliance_pct"]

        # 1. Precision Alerts
        if prec is not None:
            if prec < rules["precision_critical"]:
                h = generate_alert_hash(site, finding, priority, "AI Precision")
                active_hashes.add(h)
                current_alerts.append((h, now_ts, now_ts, "CRITICAL", site, finding, priority, "AI Precision", prec, rules["precision_critical"], f"Precision dropped to {prec}% for {finding} at {site} (Critical < {rules['precision_critical']}%)", "ACTIVE"))
            elif prec < rules["precision_warning"]:
                h = generate_alert_hash(site, finding, priority, "AI Precision")
                active_hashes.add(h)
                current_alerts.append((h, now_ts, now_ts, "WARNING", site, finding, priority, "AI Precision", prec, rules["precision_warning"], f"Precision at {prec}% for {finding} at {site} (Warning < {rules['precision_warning']}%)", "ACTIVE"))

        # 2. Recall Alerts (Warning & Critical)
        if rec is not None:
            if rec < rules["recall_critical"]:
                h = generate_alert_hash(site, finding, priority, "AI Recall")
                active_hashes.add(h)
                current_alerts.append((h, now_ts, now_ts, "CRITICAL", site, finding, priority, "AI Recall", rec, rules["recall_critical"], f"Recall dropped to {rec}% for {finding} at {site} (Critical < {rules['recall_critical']}%)", "ACTIVE"))
            elif rec < rules["recall_warning"]:
                h = generate_alert_hash(site, finding, priority, "AI Recall")
                active_hashes.add(h)
                current_alerts.append((h, now_ts, now_ts, "WARNING", site, finding, priority, "AI Recall", rec, rules["recall_warning"], f"Recall at {rec}% for {finding} at {site} (Warning < {rules['recall_warning']}%)", "ACTIVE"))

        # 3. SLA Compliance Alerts
        if comp is not None:
            if comp < rules["sla_compliance_critical"]:
                h = generate_alert_hash(site, finding, priority, "SLA Compliance")
                active_hashes.add(h)
                current_alerts.append((h, now_ts, now_ts, "CRITICAL", site, finding, priority, "SLA Compliance", comp, rules["sla_compliance_critical"], f"SLA Compliance fell to {comp}% at {site} (Critical < {rules['sla_compliance_critical']}%)", "ACTIVE"))

        # 4. p95 TAT Alerts
        target_tat = tat_targets.get(priority, 120)
        if p95_tat is not None and p95_tat > target_tat:
            h = generate_alert_hash(site, finding, priority, "p95 Turnaround Time")
            active_hashes.add(h)
            current_alerts.append((h, now_ts, now_ts, "WARNING", site, finding, priority, "p95 Turnaround Time", p95_tat, target_tat, f"p95 Latency ({p95_tat} min) exceeded {priority} SLA ({target_tat} min) at {site}", "ACTIVE"))

    # Upsert Active Alerts & Mark Resolved Alerts
    for alert in current_alerts:
        conn.execute(
            """
            INSERT INTO main_marts.fct_alert_history VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (alert_hash) DO UPDATE SET 
                last_detected_at = EXCLUDED.last_detected_at,
                observed_value = EXCLUDED.observed_value,
                severity = EXCLUDED.severity,
                status = 'ACTIVE';
        """,
            alert,
        )

    # Mark non-detected previously active alerts as RESOLVED
    if active_hashes:
        placeholders = ",".join([f"'{h}'" for h in active_hashes])
        conn.execute(f"UPDATE main_marts.fct_alert_history SET status = 'RESOLVED' WHERE alert_hash NOT IN ({placeholders});")

    active_count = conn.execute("SELECT count(*) FROM main_marts.fct_alert_history WHERE status = 'ACTIVE'").fetchone()[0]
    print(f"✓ Alert Engine finished. Currently tracking {active_count} ACTIVE alerts in persistent audit history.")
    conn.close()


if __name__ == "__main__":
    run_alert_engine()