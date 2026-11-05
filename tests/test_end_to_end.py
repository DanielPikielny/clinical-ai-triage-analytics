import duckdb
import pytest

DB_PATH = "data/clinical_warehouse.duckdb"


def test_warehouse_tables_exist_and_populated():
    conn = duckdb.connect(DB_PATH)
    conn.execute("SET search_path = 'main_marts,main_int_clinical,main_stg_clinical,main';")

    scan_count = conn.execute("SELECT COUNT(*) FROM main_stg_clinical.stg_clinical_scans").fetchone()[0]
    assert scan_count > 0, "Staging table stg_clinical_scans is empty"

    impact_count = conn.execute("SELECT COUNT(*) FROM main_marts.fct_clinical_impact").fetchone()[0]
    assert impact_count > 0, "Marts table fct_clinical_impact is empty"

    drift_count = conn.execute("SELECT COUNT(*) FROM main_marts.fct_model_drift").fetchone()[0]
    assert drift_count > 0, "Model drift table fct_model_drift is empty"

    conn.close()


def test_alert_resolution_state_behavior():
    conn = duckdb.connect(DB_PATH)
    conn.execute("SET search_path = 'main_marts,main_int_clinical,main_stg_clinical,main';")

    # Verify status values are valid lifecycle states
    statuses = set(r[0] for r in conn.execute("SELECT DISTINCT status FROM main_marts.fct_alert_history").fetchall())
    assert len(statuses) > 0, "No alert history records found"
    assert statuses.issubset({"ACTIVE", "RESOLVED"}), f"Invalid alert status found: {statuses}"

    conn.close()