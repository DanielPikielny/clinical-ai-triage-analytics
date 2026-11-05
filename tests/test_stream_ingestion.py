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


def generate_live_event(event_index):
    now = datetime.now()
    finding = random.choice(FINDING_TYPES)

    return {
        "event_id": f"EVT_LIVE_{event_index:05d}",
        "accession_number": f"ACC_{random.randint(100000, 999999)}",
        "patient_id": f"PAT_{random.randint(10000, 99999)}",
        "hospital_site_id": random.choice(HOSPITALS),
        "modality": "CT",
        "finding_type": finding,
        "clinical_priority": "EMERGENCY",
        "scan_at": now.isoformat(),
        "ai_processed_at": (now + timedelta(seconds=45)).isoformat(),
        "ai_flagged": random.random() > 0.5,
        "ai_confidence_score": round(random.uniform(0.4, 0.98), 4),
        "scanner_vendor": "Siemens Healthineers",
        "model_version": "v1.2",
    }


def start_streaming_producer(num_events=10, delay_seconds=0.2):
    print(f"Starting Live Event Stream Producer ({num_events} events)...\n")

    for i in range(1, num_events + 1):
        event = generate_live_event(i)
        ingest_event_batch([event])
        time.sleep(delay_seconds)

    print("\n✓ Live event stream simulation complete!")


if __name__ == "__main__":
    start_streaming_producer(num_events=10)