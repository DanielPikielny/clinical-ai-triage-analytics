import json
import random
from datetime import datetime, timedelta
import duckdb
from faker import Faker

fake = Faker()
Faker.seed(42)
random.seed(42)

DB_PATH = "data/clinical_warehouse.duckdb"
NUM_RECORDS = 1500


def generate_clinical_event(event_id: int):
    scan_dt = datetime.now() - timedelta(
        days=random.randint(0, 30),
        hours=random.randint(0, 23),
        minutes=random.randint(0, 59),
    )

    finding_catalog = [
        {"modality": "CT", "finding": "Intracranial Hemorrhage", "priority": "EMERGENCY"},
        {"modality": "CT", "finding": "Pulmonary Embolism", "priority": "EMERGENCY"},
        {"modality": "CT", "finding": "Cervical Spine Fracture", "priority": "URGENT"},
        {"modality": "XR", "finding": "Pneumothorax", "priority": "URGENT"},
        {"modality": "MRI", "finding": "Acute Ischemic Stroke", "priority": "EMERGENCY"},
    ]

    selected_finding = random.choice(finding_catalog)

    ai_processed_dt = scan_dt + timedelta(seconds=random.randint(60, 300))

    ai_flagged = random.choices([True, False], weights=[0.35, 0.65])[0]

    if ai_flagged and selected_finding["priority"] == "EMERGENCY":
        review_delay_minutes = random.randint(5, 35)
    else:
        review_delay_minutes = random.randint(40, 240)

    if random.random() < 0.05:
        clinician_reviewed_dt = None
        clinician_confirmed = None
    else:
        clinician_reviewed_dt = scan_dt + timedelta(minutes=review_delay_minutes)
        if ai_flagged:
            clinician_confirmed = random.choices([True, False], weights=[0.85, 0.15])[0]
        else:
            clinician_confirmed = random.choices([True, False], weights=[0.05, 0.95])[0]

    hospital_site_id = f"HOSP_{random.randint(101, 108)}"

    return {
        "event_id": f"EVT-{event_id:06d}",
        "accession_number": f"ACC-{random.randint(10000000, 99999999)}",
        "patient_id": f"PAT-{random.randint(100000, 999999)}",
        "hospital_site_id": hospital_site_id,
        "modality": selected_finding["modality"],
        "finding_type": selected_finding["finding"],
        "clinical_priority": selected_finding["priority"],
        "scan_timestamp": scan_dt.isoformat(),
        "ai_processed_timestamp": ai_processed_dt.isoformat(),
        "ai_flagged": ai_flagged,
        "clinician_reviewed_timestamp": clinician_reviewed_dt.isoformat()
        if clinician_reviewed_dt
        else None,
        "clinician_confirmed": clinician_confirmed,
        "raw_json_payload": json.dumps(
            {
                "scanner_vendor": random.choice(["GE", "Siemens", "Philips"]),
                "slice_thickness_mm": random.choice([0.625, 1.25, 2.5, 5.0]),
                "ai_model_version": "v2.4.1",
                "ai_confidence_score": round(random.uniform(0.55, 0.99), 4)
                if ai_flagged
                else round(random.uniform(0.01, 0.45), 4),
            }
        ),
    }


def populate_duckdb():
    print(f"Generating {NUM_RECORDS} synthetic clinical records...")
    records = [generate_clinical_event(i) for i in range(1, NUM_RECORDS + 1)]

    conn = duckdb.connect(DB_PATH)
    conn.execute("DROP TABLE IF EXISTS raw_staging.raw_ai_scans;")
    conn.execute(
        """
        CREATE TABLE raw_staging.raw_ai_scans (
            event_id VARCHAR,
            accession_number VARCHAR,
            patient_id VARCHAR,
            hospital_site_id VARCHAR,
            modality VARCHAR,
            finding_type VARCHAR,
            clinical_priority VARCHAR,
            scan_timestamp VARCHAR,
            ai_processed_timestamp VARCHAR,
            ai_flagged BOOLEAN,
            clinician_reviewed_timestamp VARCHAR,
            clinician_confirmed BOOLEAN,
            raw_json_payload VARCHAR
        );
    """
    )
    import pandas as pd

    df = pd.DataFrame(records)
    conn.execute("INSERT INTO raw_staging.raw_ai_scans SELECT * FROM df")
    count = conn.execute(
        "SELECT COUNT(*) FROM raw_staging.raw_ai_scans;"
    ).fetchone()[0]
    print(
        f"  ✓ Successfully loaded {count} records into raw_staging.raw_ai_scans!"
    )

    conn.close()


if __name__ == "__main__":
    populate_duckdb()