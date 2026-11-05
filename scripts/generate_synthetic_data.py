import argparse
import os
import random
from datetime import datetime, timedelta
import duckdb
import numpy as np
import pandas as pd

DB_PATH = "data/clinical_warehouse.duckdb"

CLINICAL_CATALOG = {
    "Intracranial Hemorrhage": {"modality": "CT", "default_priority": "EMERGENCY"},
    "Pulmonary Embolism": {"modality": "CT", "default_priority": "EMERGENCY"},
    "Acute Ischemic Stroke": {"modality": "MRI", "default_priority": "EMERGENCY"},
    "Cervical Spine Fracture": {"modality": "CT", "default_priority": "URGENT"},
    "Pneumothorax": {"modality": "XR", "default_priority": "URGENT"},
}

HOSPITAL_SITES = [f"HOSP_{i}" for i in range(101, 109)]
VENDORS = ["GE Healthcare", "Siemens Healthineers", "Philips Healthcare"]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Generate synthetic clinical AI triage data."
    )
    parser.add_argument(
        "--num-records", type=int, default=2000, help="Number of records to generate"
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed for reproducibility"
    )
    parser.add_argument(
        "--scenario",
        type=str,
        default="normal",
        choices=["normal", "model_degradation", "hospital_overload", "model_update"],
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
        
        # Enforce realistic clinical matrix pairing
        finding = random.choice(list(CLINICAL_CATALOG.keys()))
        modality = CLINICAL_CATALOG[finding]["modality"]
        priority = CLINICAL_CATALOG[finding]["default_priority"]
        
        # 15% random variance in priority level for clinical triage realistic noise
        if random.random() < 0.15:
            priority = random.choice(["EMERGENCY", "URGENT", "ROUTINE"])

        vendor = random.choice(VENDORS)
        scan_offset_mins = random.randint(0, 30 * 24 * 60)
        scan_at = base_time + timedelta(minutes=scan_offset_mins)

        # AI Processing Latency
        ai_proc_delay = round(random.uniform(0.5, 3.0), 2)
        if scenario == "hospital_overload" and site == "HOSP_104" and random.random() < 0.25:
            ai_proc_delay += round(random.uniform(15.0, 45.0), 2)
        ai_processed_at = scan_at + timedelta(minutes=ai_proc_delay)

        # Model Versioning & Performance Behavior Shift
        if scenario == "model_update":
            model_version = "v1.2" if scan_at > (base_time + timedelta(days=15)) else "v1.0"
        else:
            model_version = "v1.0"

        # Well-Calibrated AI Confidence Score Simulation
        # Ground truth status drives score distribution so confidence maps to accuracy
        ground_truth_positive = random.random() < 0.35  # ~35% true disease prevalence

        if ground_truth_positive:
            # Positive cases skewed toward higher confidence (mean ~0.85)
            if scenario == "model_degradation" and site == "HOSP_104" and finding == "Pulmonary Embolism":
                # Degraded model assigns low confidence to positive cases (high false negatives)
                ai_confidence = round(float(np.clip(np.random.beta(2, 5), 0.05, 0.99)), 4)
            elif scenario == "model_update" and model_version == "v1.2":
                # Upgraded model produces sharper, well-separated confidence scores
                ai_confidence = round(float(np.clip(np.random.beta(8, 2), 0.05, 0.99)), 4)
            else:
                ai_confidence = round(float(np.clip(np.random.beta(6, 2), 0.05, 0.99)), 4)
        else:
            # Negative cases skewed toward lower confidence (mean ~0.15)
            if scenario == "model_degradation" and site == "HOSP_104" and finding == "Pulmonary Embolism":
                # Degraded model assigns high confidence to negative cases (high false positives)
                ai_confidence = round(float(np.clip(np.random.beta(4, 3), 0.05, 0.99)), 4)
            else:
                ai_confidence = round(float(np.clip(np.random.beta(1.5, 6), 0.05, 0.99)), 4)

        ai_flagged = ai_confidence >= 0.60

        # Clinician Review Workflow
        is_reviewed = random.random() > 0.08  # 8% pending review cases

        if is_reviewed:
            if priority == "EMERGENCY":
                tat_base = random.randint(15, 40)
            elif priority == "URGENT":
                tat_base = random.randint(45, 110)
            else:
                tat_base = random.randint(120, 280)

            if scenario == "hospital_overload" and site == "HOSP_101":
                tat_base = int(tat_base * 2.2)

            total_tat = max(int(ai_proc_delay + 1), tat_base)
            clinician_reviewed_at = scan_at + timedelta(minutes=total_tat)
            clinician_confirmed = ground_truth_positive
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
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = duckdb.connect(DB_PATH)
    conn.execute("TRUNCATE TABLE raw_staging.raw_ai_scans;")
    conn.register("df_view", df)
    conn.execute("INSERT INTO raw_staging.raw_ai_scans SELECT * FROM df_view;")
    conn.close()

    print(f"✓ Successfully seeded {len(df)} realistic records into raw_staging.raw_ai_scans!")


if __name__ == "__main__":
    args = parse_args()
    generate_data(num_records=args.num_records, seed=args.seed, scenario=args.scenario)