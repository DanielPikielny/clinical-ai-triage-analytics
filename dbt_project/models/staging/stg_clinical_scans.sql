WITH raw_scans AS (
    SELECT * FROM {{ source('raw_staging', 'raw_ai_scans') }}
)

SELECT
    event_id,
    accession_number,
    patient_id,
    hospital_site_id,
    modality,
    finding_type,
    clinical_priority,
    
    -- Timestamp conversions
    TRY_CAST(scan_timestamp AS TIMESTAMP) AS scan_at,
    TRY_CAST(ai_processed_timestamp AS TIMESTAMP) AS ai_processed_at,
    TRY_CAST(clinician_reviewed_timestamp AS TIMESTAMP) AS clinician_reviewed_at,
    
    -- Boolean flags
    ai_flagged,
    clinician_confirmed,
    
    -- Extract values from JSON payload
    json_extract_string(raw_json_payload, '$.scanner_vendor') AS scanner_vendor,
    CAST(json_extract_string(raw_json_payload, '$.ai_confidence_score') AS DOUBLE) AS ai_confidence_score,

    -- Calculate core intervals in minutes
    DATEDIFF('minute', TRY_CAST(scan_timestamp AS TIMESTAMP), TRY_CAST(ai_processed_timestamp AS TIMESTAMP)) AS scan_to_ai_minutes,
    DATEDIFF('minute', TRY_CAST(scan_timestamp AS TIMESTAMP), TRY_CAST(clinician_reviewed_timestamp AS TIMESTAMP)) AS total_turnaround_minutes

FROM raw_scans