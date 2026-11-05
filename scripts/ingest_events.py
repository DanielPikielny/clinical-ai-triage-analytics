import json
import os
from datetime import datetime
import duckdb

DB_PATH = "data/clinical_warehouse.duckdb"


def validate_event_payload(payload):
    """Enforces JSON event schema contract."""
    required_fields = [
        "event_id",
        "accession_number",
        "patient_id",
        "hospital_site_id",
        "modality",
        "finding_type",
        "clinical_priority",
        "scan_at",
    ]
    for field in required_fields:
        if field not in payload:
            raise ValueError(f"Missing required schema field: {field}")
    return True


def ingest_event_batch(events_json_list):
    """Ingests a micro-batch of JSON events into DuckDB using idempotent upserts."""
    conn = duckdb.connect(DB_PATH)
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw_staging;")

    valid_records = []
    for raw_event in events_json_list:
        try:
            payload = (
                json.loads(raw_event)
                if isinstance(raw_event, str)
                else raw_event
            )
            validate_event_payload(payload)

            valid_records.append(
                (
                    payload["event_id"],
                    payload["accession_number"],
                    payload["patient_id"],
                    payload["hospital_site_id"],
                    payload["modality"],
                    payload["finding_type"],
                    payload["clinical_priority"],
                    payload["scan_at"],
                    payload.get("ai_processed_at"),
                    payload.get("clinician_reviewed_at"),
                    payload.get("ai_flagged", False),
                    payload.get("clinician_confirmed"),
                    payload.get("scanner_vendor", "GE Healthcare"),
                    payload.get("model_version", "v1.0"),
                    payload.get("ai_confidence_score", 0.0),
                )
            )
        except Exception as e:
            print(f"Event validation failed: {e}")

    if valid_records:
        conn.executemany(
            """
            INSERT INTO raw_staging.raw_ai_scans VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (event_id) DO UPDATE SET
                ai_processed_at = EXCLUDED.ai_processed_at,
                clinician_reviewed_at = EXCLUDED.clinician_reviewed_at,
                ai_flagged = EXCLUDED.ai_flagged,
                clinician_confirmed = EXCLUDED.clinician_confirmed,
                ai_confidence_score = EXCLUDED.ai_confidence_score;
        """,
            valid_records,
        )
        print(f"✓ Successfully ingested {len(valid_records)} streaming events.")

    conn.close()


if __name__ == "__main__":
    # Test execution with dummy JSON payload
    sample_event = {
        "event_id": "EVT_STRM_001",
        "accession_number": "ACC_999999",
        "patient_id": "PAT_88888",
        "hospital_site_id": "HOSP_101",
        "modality": "CT",
        "finding_type": "Pulmonary Embolism",
        "clinical_priority": "EMERGENCY",
        "scan_at": datetime.now().isoformat(),
        "ai_processed_at": datetime.now().isoformat(),
        "ai_flagged": True,
        "ai_confidence_score": 0.94,
    }
    ingest_event_batch([sample_event])