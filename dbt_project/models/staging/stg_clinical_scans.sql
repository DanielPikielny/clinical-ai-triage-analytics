{{
    config(
        materialized='incremental',
        unique_key='event_id'
    )
}}

with raw_data as (
    select * from raw_staging.raw_ai_scans
    {% if is_incremental() %}
        -- 3-day overlapping window ensures delayed clinician reviews update existing records
        where scan_at >= (select coalesce(max(scan_timestamp) - interval '3 days', '1970-01-01'::timestamp) from {{ this }})
    {% endif %}
)

select
    event_id,
    accession_number,
    patient_id,
    hospital_site_id,
    modality,
    finding_type,
    upper(clinical_priority) as clinical_priority,
    scan_at as scan_timestamp,
    ai_processed_at as ai_processed_timestamp,
    clinician_reviewed_at as clinician_reviewed_timestamp,
    ai_flagged,
    clinician_confirmed,
    scanner_vendor,
    model_version,
    ai_confidence_score,
    case 
        when clinician_reviewed_at is not null then true 
        else false 
    end as is_reviewed
from raw_data