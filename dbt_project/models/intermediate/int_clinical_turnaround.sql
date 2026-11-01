WITH stg_scans AS (
    SELECT * FROM {{ ref('stg_clinical_scans') }}
)

SELECT
    event_id,
    accession_number,
    patient_id,
    hospital_site_id,
    modality,
    finding_type,
    clinical_priority,
    scan_at,
    ai_processed_at,
    clinician_reviewed_at,
    ai_flagged,
    clinician_confirmed,
    scanner_vendor,
    ai_confidence_score,
    scan_to_ai_minutes,
    total_turnaround_minutes,

    -- Classify detection accuracy
    CASE
        WHEN ai_flagged AND clinician_confirmed THEN 'TRUE_POSITIVE'
        WHEN ai_flagged AND NOT clinician_confirmed THEN 'FALSE_POSITIVE'
        WHEN NOT ai_flagged AND clinician_confirmed THEN 'FALSE_NEGATIVE'
        ELSE 'TRUE_NEGATIVE'
    END AS ai_detection_classification,

    -- Categorize SLA / Turnaround Performance
    CASE
        WHEN total_turnaround_minutes IS NULL THEN 'PENDING_REVIEW'
        WHEN total_turnaround_minutes <= 30 THEN 'WITHIN_TARGET'
        WHEN total_turnaround_minutes <= 60 THEN 'MODERATE_DELAY'
        ELSE 'SEVERE_DELAY'
    END AS turnaround_performance_category

FROM stg_scans