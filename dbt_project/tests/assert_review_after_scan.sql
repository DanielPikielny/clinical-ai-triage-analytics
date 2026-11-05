-- Singular assertion verifying clinician review timestamp never precedes scan acquisition
select
    event_id,
    scan_timestamp,
    clinician_reviewed_timestamp
from {{ ref('stg_clinical_scans') }}
where clinician_reviewed_timestamp is not null
  and clinician_reviewed_timestamp < scan_timestamp