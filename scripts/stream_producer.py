import sys
import os
import random
import time
from datetime import datetime, timedelta

# Ensure project root is in sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scripts.ingest_events import ingest_event_batch

FINDING_TYPES = [
    "Pulmonary Embolism",
    "Intracranial Hemorrhage",
    "Acute Ischemic Stroke",
]
HOSPITALS = ["HOSP_101", "HOSP_102", "HOSP_103", "HOSP_104"]


def simulate_lifecycle_stream(num_scans=5):
    """Simulates multi-stage DICOM lifecycle event streams (Acquired -> AI Processed -> Clinician Reviewed)."""
    print(f"Starting Multi-Stage Lifecycle Event Stream ({num_scans} scans)...\n")

    for i in range(1, num_scans + 1):
        event_id = f"EVT_LIVE_V12_{i:04d}"
        acc_num = f"ACC_{random.randint(100000, 999999)}"
        pat_id = f"PAT_{random.randint(10000, 99999)}"
        site = random.choice(HOSPITALS)
        finding = random.choice(FINDING_TYPES)
        now = datetime.now()

        # Stage 1: SCAN_ACQUIRED
        scan_event = {
            "event_id": event_id,
            "accession_number": acc_num,
            "patient_id": pat_id,
            "hospital_site_id": site,
            "modality": "CT",
            "finding_type": finding,
            "clinical_priority": "EMERGENCY",
            "scan_at": now.isoformat(),
            "scanner_vendor": "Siemens Healthineers",
            "model_version": "v1.2",
        }
        print(f"[Event 1/3] Emitting SCAN_ACQUIRED for {event_id} ({finding} at {site})")
        ingest_event_batch([scan_event])
        time.sleep(0.1)

        # Stage 2: AI_PROCESSED (45 seconds later)
        ai_flagged = random.random() > 0.3
        conf_score = round(random.uniform(0.75, 0.98) if ai_flagged else random.uniform(0.05, 0.35), 4)
        ai_event = {
            **scan_event,
            "ai_processed_at": (now + timedelta(seconds=45)).isoformat(),
            "ai_flagged": ai_flagged,
            "ai_confidence_score": conf_score,
        }
        print(f"[Event 2/3] Emitting AI_PROCESSED for {event_id} (Confidence: {conf_score})")
        ingest_event_batch([ai_event])
        time.sleep(0.1)

        # Stage 3: CLINICIAN_REVIEWED (25 minutes later)
        # Model v1.2 has 90% positive correlation with AI prediction
        confirmed = ai_flagged if random.random() < 0.9 else not ai_flagged
        review_event = {
            **ai_event,
            "clinician_reviewed_at": (now + timedelta(minutes=25)).isoformat(),
            "clinician_confirmed": confirmed,
        }
        print(f"[Event 3/3] Emitting CLINICIAN_REVIEWED for {event_id} (Confirmed: {confirmed})\n")
        ingest_event_batch([review_event])
        time.sleep(0.1)

    print("✓ Lifecycle event stream simulation complete!")


if __name__ == "__main__":
    simulate_lifecycle_stream(num_scans=5)