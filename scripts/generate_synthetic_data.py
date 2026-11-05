import argparse
import random
from datetime import datetime, timedelta
import duckdb
import numpy as np
import pandas as pd

DB_PATH = "data/clinical_warehouse.duckdb"

FINDING_TYPES = [
    "Intracranial Hemorrhage",
    "Pulmonary Embolism",
    "Acute Ischemic Stroke",
    "Cervical Spine Fracture",
    "Pneumothorax",
]

HOSPITAL_SITES = [f"HOSP_{i}" for i in range(101, 109)]
MODALITIES = ["CT", "XR", "MRI"]
VENDORS = ["GE Healthcare", "Siemens Healthineers", "Philips Healthcare"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate synthetic clinical AI triage data."
    )
    parser.add_argument(
        "--num-records",
        type=int,
        default=2000,
        help="Number of records to generate",
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="normal",
        choices=[
            "normal",
            "model_degradation",
            "hospital_overload",
            "model_update",
        ],
        help="Simulated operational scenario",
    )
    return parser.parse_args()


def generate_data(num_records=2000, seed=42, scenario="normal"):
    random.seed(seed)
    np.random.seed(seed)

    print(
        f"Generating {num_records} clinical records (Seed: {seed}, Scenario: {scenario})..."
    )

    base_time = datetime.now() - timedelta(days=30)
    data = []

    for i in range(1, num_records + 1):
        event_id = f"EVT_{i:06d}"
        accession_number = f"ACC_{random.randint(100000, 999999)}"
        patient_id = f"PAT_{random.randint(10000, 99999)}"
        site = random.choice(HOSPITAL_SITES)
        finding = random.choice(FINDING_TYPES)
        modality = random.choice(MODALITIES)
        vendor = random.choice(VENDORS)

        # Priority distribution
        priority = np.random.choice(
            ["EMERGENCY", "URGENT", "ROUTINE"], p=[0.25, 0.45, 0.30]
        )

        # Time series timestamps over 30 days
        scan_offset_mins = random.randint(0, 30 * 24 * 60)
        scan_at = base_time + timedelta(minutes=scan_offset_mins)

        # AI processing time (0.5 to 3 minutes)
        ai_proc_delay = round(random.uniform(0.5, 3.0), 2)
        if scenario == "hospital_overload" and random.random() < 0.15:
            ai_proc_delay += round(random.uniform(10.0, 30.0), 2)
        ai_processed_at = scan_at + timedelta(minutes=ai_proc_delay)

        # Model Version Tagging
        if scenario == "model_update":
            # Transition to v1.2 midway through month
            model_version = (
                "v1.2"
                if scan_at > (base_time + timedelta(days=15))
                else "v1.0"
            )
        else:
            model_version = "v1.0"

        # AI Confidence & Flagging Logic
        base_confidence = random.uniform(0.10, 0.98)

        # Apply scenario logic to confidence/flagging
        if (
            scenario == "model_degradation"
            and site == "HOSP_104"
            and finding == "Pulmonary Embolism"
        ):
            # Model drift: lower confidence and higher false flags
            base_confidence = random.uniform(0.40, 0.75)

        ai_confidence = round(base_confidence, 4)
        ai_flagged = ai_confidence >= 0.60

        # Ground Truth & Clinician Review Logic
        # 10% of scans remain unreviewed (PENDING_REVIEW)
        is_reviewed = random.random() > 0.10

        if is_reviewed:
            # Turnaround time generation
            if priority == "EMERGENCY":
                tat_base = random.randint(15, 40)
            elif priority == "URGENT":
                tat_base = random.randint(45, 110)
            else:
                tat_base = random.randint(120, 300)

            # Scenario adjustments for TAT
            if scenario == "hospital_overload" and site == "HOSP_101":
                tat_base = int(tat_base * 2.5)  # Heavy review delays

            total_tat = max(int(ai_proc_delay + 1), tat_base)
            clinician_reviewed_at = scan_at + timedelta(minutes=total_tat)

            # Clinician Agreement (Ground Truth Proxy)
            if ai_flagged:
                # Target ~80% baseline precision, lower in degradation scenario
                true_pos_prob = (
                    0.50
                    if (
                        scenario == "model_degradation"
                        and site == "HOSP_104"
                        and finding == "Pulmonary Embolism"
                    )
                    else 0.82
                )
                clinician_confirmed = random.random() < true_pos_prob
            else:
                # False negative rate ~3%
                clinician_confirmed = random.random() < 0.03
        else:
            clinician_reviewed_at = None
            clinician_confirmed = None

        data.append(
            (
                event_id,
                accession_number,
                patient_id,
                site,
                modality,
                finding,
                priority,
                scan_at,
                ai_processed_at,
                clinician_reviewed_at,
                ai_flagged,
                clinician_confirmed,
                vendor,
                model_version,
                ai_confidence,
            )
        )

    columns = [
        "event_id",
        "accession_number",
        "patient_id",
        "hospital_site_id",
        "modality",
        "finding_type",
        "clinical_priority",
        "scan_at",
        "ai_processed_at",
        "clinician_reviewed_at",
        "ai_flagged",
        "clinician_confirmed",
        "scanner_vendor",
        "model_version",
        "ai_confidence_score",
    ]

    df = pd.DataFrame(data, columns=columns)

    conn = duckdb.connect(DB_PATH)
    conn.execute(
        "TRUNCATE TABLE raw_staging.raw_ai_scans;"
    )  # Clean table prior to seed
    conn.register("df_view", df)
    conn.execute(
        "INSERT INTO raw_staging.raw_ai_scans SELECT * FROM df_view;"
    )
    conn.close()

    print(
        f"✓ Successfully seeded {len(df)} records into raw_staging.raw_ai_scans!"
    )


if __name__ == "__main__":
    args = parse_args()
    generate_data(
        num_records=args.num_records, seed=args.seed, scenario=args.scenario
    )