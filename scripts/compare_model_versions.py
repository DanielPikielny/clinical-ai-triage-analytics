import duckdb
import pandas as pd

DB_PATH = "data/clinical_warehouse.duckdb"


def run_version_comparison():
    conn = duckdb.connect(DB_PATH)
    conn.execute(
        "SET search_path ="
        " 'main_marts,main_int_clinical,main_stg_clinical,main';"
    )

    print("Executing Model Version Impact Analysis (v1.0 vs v1.2)...\n")

    query = """
        SELECT 
            model_version,
            COUNT(event_id) as total_scans,
            SUM(is_reviewed::INT) as reviewed_scans,
            ROUND((SUM(is_tp)::DOUBLE / NULLIF(SUM(is_tp) + SUM(is_fp), 0)) * 100.0, 2) as precision_pct,
            ROUND((SUM(is_tp)::DOUBLE / NULLIF(SUM(is_tp) + SUM(is_fn), 0)) * 100.0, 2) as recall_pct,
            ROUND(AVG(total_turnaround_minutes), 1) as avg_tat_mins,
            QUANTILE_CONT(total_turnaround_minutes, 0.95) as p95_tat_mins,
            ROUND((SUM(CASE WHEN met_sla = true THEN 1 ELSE 0 END)::DOUBLE / NULLIF(SUM(is_reviewed::INT), 0)) * 100.0, 2) as sla_compliance_pct
        FROM main_int_clinical.int_clinical_turnaround
        GROUP BY model_version
        ORDER BY model_version;
    """

    df = conn.execute(query).df()
    print(df.to_string(index=False))
    conn.close()


if __name__ == "__main__":
    run_version_comparison()