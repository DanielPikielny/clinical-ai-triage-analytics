import os
import duckdb

DB_PATH = "data/clinical_warehouse.duckdb"


def init_db():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = duckdb.connect(DB_PATH)
    print(f"Initializing DuckDB at {DB_PATH}...")

    conn.execute("CREATE SCHEMA IF NOT EXISTS raw_staging;")
    conn.execute("CREATE SCHEMA IF NOT EXISTS stg_clinical;")
    conn.execute("CREATE SCHEMA IF NOT EXISTS int_clinical;")
    conn.execute("CREATE SCHEMA IF NOT EXISTS marts;")
    conn.execute("CREATE SCHEMA IF NOT EXISTS main_marts;")

    conn.execute("DROP TABLE IF EXISTS raw_staging.raw_ai_scans;")

    conn.execute(
        """
        CREATE TABLE raw_staging.raw_ai_scans (
            event_id VARCHAR PRIMARY KEY,
            accession_number VARCHAR,
            patient_id VARCHAR,
            hospital_site_id VARCHAR,
            modality VARCHAR,
            finding_type VARCHAR,
            clinical_priority VARCHAR,
            scan_at TIMESTAMP,
            ai_processed_at TIMESTAMP,
            clinician_reviewed_at TIMESTAMP,
            ai_flagged BOOLEAN,
            clinician_confirmed BOOLEAN,
            scanner_vendor VARCHAR,
            model_version VARCHAR,
            ai_confidence_score DOUBLE
        );
    """
    )

    print("✓ Schema and tables initialized successfully!")
    conn.close()


if __name__ == "__main__":
    init_db()