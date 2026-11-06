import json
import os
from datetime import datetime
import duckdb

DB_PATH = "data/clinical_warehouse.duckdb"
VALID_PRIORITIES = {"EMERGENCY", "URGENT", "ROUTINE"}
VALID_MODALITIES = {"CT", "MRI", "XR", "US"}


def validate_event_payload(payload):
    """Enforces strict value boundaries, field types, and range constraints."""
    if not isinstance(payload, dict):
        raise ValueError("Event payload must be a JSON object (dictionary)")

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
        if field not in payload or payload[field] is None:
            raise ValueError(f"Missing required field: {field}")

    if not str(payload["event_id"]).strip():
        raise ValueError("event_id cannot be empty")

    if payload["modality"] not in VALID_MODALITIES:
        raise ValueError(f"Invalid modality: {payload['modality']}")

    if str(payload["clinical_priority"]).upper() not in VALID_PRIORITIES:
        raise ValueError(
            f"Invalid clinical_priority: {payload['clinical_priority']}"
        )

    conf = payload.get("ai_confidence_score")
    if conf is not None:
        if not isinstance(conf, (int, float)) or not (0.0 <= float(conf) <= 1.0):
            raise ValueError(
                f"ai_confidence_score must be numeric between 0.0 and 1.0, got: {conf}"
            )

    try:
        datetime.fromisoformat(str(payload["scan_at"]).replace("Z", "+00:00"))
    except Exception:
        raise ValueError(f"Invalid scan_at ISO timestamp: {payload['scan_at']}")

    return True


def ingest_event_batch(events_json_list):
    """Ingests micro-batches into DuckDB with safe payload exception isolation."""
    conn = duckdb.connect(DB_PATH)
    conn.execute("CREATE SCHEMA IF NOT EXISTS raw_staging;")

    accepted_records = []
    errors = []

    for raw_event in events_json_list:
        payload = None
        event_id = "UNKNOWN"
        try:
            if isinstance(raw_event, str):
                payload = json.loads(raw_event)
            else:
                payload = raw_event

            if isinstance(payload, dict):
                event_id = payload.get("event_id", "UNKNOWN")

            validate_event_payload(payload)

            accepted_records.append(
                (
                    payload["event_id"],
                    payload["accession_number"],
                    payload["patient_id"],
                    payload["hospital_site_id"],
                    payload["modality"],
                    payload["finding_type"],
                    str(payload["clinical_priority"]).upper(),
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
            errors.append({"event_id": event_id, "error": str(e)})

    if accepted_records:
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
            accepted_records,
        )

    conn.close()

    result_summary = {
        "accepted_count": len(accepted_records),
        "rejected_count": len(errors),
        "errors": errors,
    }

    if accepted_records:
        print(
            f"Ingested {result_summary['accepted_count']} events (Rejected:"
            f" {result_summary['rejected_count']})."
        )
    return result_summary


if __name__ == "__main__":
    sample_event = {
        "event_id": "EVT_STRM_001",
        "accession_number": "ACC_999999",
        "patient_id": "PAT_88888",
        "hospital_site_id": "HOSP_101",
        "modality": "CT",
        "finding_type": "Pulmonary Embolism",
        "clinical_priority": "EMERGENCY",
        "scan_at": datetime.now().isoformat(),
        "ai_confidence_score": 0.94,
    }
    ingest_event_batch([sample_event])