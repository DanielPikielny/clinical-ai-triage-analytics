-- Custom Singular Test: In dbt, a singular test fails if it returns ANY rows.
-- This test flags records where the clinician review timestamp occurs BEFORE the scan timestamp.

SELECT
    event_id,
    scan_at,
    clinician_reviewed_at,
    total_turnaround_minutes
FROM {{ ref('stg_clinical_scans') }}
WHERE clinician_reviewed_at IS NOT NULL
  AND clinician_reviewed_at < scan_at