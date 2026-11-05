with staging as (
    select * from {{ ref('stg_clinical_scans') }}
),

classified as (
    select
        *,
        date_diff('minute', scan_timestamp, clinician_reviewed_timestamp) as total_turnaround_minutes,
        date_diff('second', scan_timestamp, ai_processed_timestamp) / 60.0 as ai_processing_minutes,

        -- Standardized SLA Target (Minutes)
        case 
            when clinical_priority = 'EMERGENCY' then 45
            when clinical_priority = 'URGENT' then 120
            else 240
        end as target_sla_minutes,

        -- ML Confusion Matrix Classifications
        case
            when is_reviewed = false then 'PENDING_REVIEW'
            when ai_flagged = true and clinician_confirmed = true then 'TRUE_POSITIVE'
            when ai_flagged = true and clinician_confirmed = false then 'FALSE_POSITIVE'
            when ai_flagged = false and clinician_confirmed = false then 'TRUE_NEGATIVE'
            when ai_flagged = false and clinician_confirmed = true then 'FALSE_NEGATIVE'
        end as ai_classification,

        -- Confusion Matrix Binary Flags
        case when is_reviewed = true and ai_flagged = true and clinician_confirmed = true then 1 else 0 end as is_tp,
        case when is_reviewed = true and ai_flagged = true and clinician_confirmed = false then 1 else 0 end as is_fp,
        case when is_reviewed = true and ai_flagged = false and clinician_confirmed = false then 1 else 0 end as is_tn,
        case when is_reviewed = true and ai_flagged = false and clinician_confirmed = true then 1 else 0 end as is_fn,
        case when is_reviewed = false then 1 else 0 end as is_pending
    from staging
)

select
    *,
    case 
        when is_reviewed = true and total_turnaround_minutes <= target_sla_minutes then true
        when is_reviewed = true and total_turnaround_minutes > target_sla_minutes then false
        else null
    end as met_sla
from classified