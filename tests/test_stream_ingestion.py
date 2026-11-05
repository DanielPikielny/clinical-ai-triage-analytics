import pytest
from datetime import datetime
from scripts.ingest_events import validate_event_payload, ingest_event_batch


def test_valid_event_schema():
    valid_payload = {
        "event_id": "EVT_TEST_01",
        "accession_number": "ACC_123",
        "patient_id": "PAT_123",
        "hospital_site_id": "HOSP_101",
        "modality": "CT",
        "finding_type": "Pulmonary Embolism",
        "clinical_priority": "EMERGENCY",
        "scan_at": "2026-05-01T12:00:00",
        "ai_confidence_score": 0.85,
    }
    assert validate_event_payload(valid_payload) is True


def test_confidence_score_out_of_bounds():
    invalid_payload = {
        "event_id": "EVT_TEST_02",
        "accession_number": "ACC_123",
        "patient_id": "PAT_123",
        "hospital_site_id": "HOSP_101",
        "modality": "CT",
        "finding_type": "Pulmonary Embolism",
        "clinical_priority": "EMERGENCY",
        "scan_at": "2026-05-01T12:00:00",
        "ai_confidence_score": 1.5,  # Out of range (> 1.0)
    }
    with pytest.raises(ValueError, match="ai_confidence_score must be numeric between 0.0 and 1.0"):
        validate_event_payload(invalid_payload)


def test_invalid_clinical_priority():
    invalid_payload = {
        "event_id": "EVT_TEST_03",
        "accession_number": "ACC_123",
        "patient_id": "PAT_123",
        "hospital_site_id": "HOSP_101",
        "modality": "CT",
        "finding_type": "Pulmonary Embolism",
        "clinical_priority": "SUPER_CRITICAL",  # Invalid priority
        "scan_at": "2026-05-01T12:00:00",
    }
    with pytest.raises(ValueError, match="Invalid clinical_priority"):
        validate_event_payload(invalid_payload)


def test_ingest_batch_metrics_return():
    valid_event = {
        "event_id": "EVT_TEST_METRIC_1",
        "accession_number": "ACC_123",
        "patient_id": "PAT_123",
        "hospital_site_id": "HOSP_101",
        "modality": "CT",
        "finding_type": "Pulmonary Embolism",
        "clinical_priority": "EMERGENCY",
        "scan_at": datetime.now().isoformat(),
        "ai_confidence_score": 0.90,
    }
    invalid_event = {
        "event_id": "EVT_TEST_METRIC_2",
        "modality": "CT",  # Missing fields
    }

    results = ingest_event_batch([valid_event, invalid_event])
    assert results["accepted_count"] == 1
    assert results["rejected_count"] == 1