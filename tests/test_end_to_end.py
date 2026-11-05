import duckdb
import pytest

DB_PATH = "data/clinical_warehouse.duckdb"


def test_warehouse_tables_exist_and_populated():
    conn = duckdb.connect(DB_PATH)
    conn.execute(
        "SET search_path ="
        " 'main_marts,main_int_clinical,main_stg_clinical,main';"
    )

    # 1. Check Staging Table
    scan_count = conn.execute(
        "SELECT COUNT(*) FROM main_stg_clinical.stg_clinical_scans"
    ).fetchone()[0]
    assert scan_count > 0, "Staging table stg_clinical_scans is empty"

    # 2. Check Marts Table
    impact_count = conn.execute(
        "SELECT COUNT(*) FROM main_marts.fct_clinical_impact"
    ).fetchone()[0]
    assert impact_count > 0, "Marts table fct_clinical_impact is empty"

    # 3. Check Persistent Alert History
    alert_count = conn.execute(
        "SELECT COUNT(*) FROM main_marts.fct_alert_history"
    ).fetchone()[0]
    assert (
        alert_count >= 0
    ), "Alert history table main_marts.fct_alert_history inaccessible"

    # 4. Check Model Drift Analysis
    drift_count = conn.execute(
        "SELECT COUNT(*) FROM main_marts.fct_model_drift"
    ).fetchone()[0]
    assert drift_count > 0, "Model drift table fct_model_drift is empty"

    conn.close()