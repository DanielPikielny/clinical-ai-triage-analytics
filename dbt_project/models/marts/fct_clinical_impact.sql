with int_data as (
    select * from {{ ref('int_clinical_turnaround') }}
)

select
    hospital_site_id,
    modality,
    finding_type,
    clinical_priority,
    model_version,

    -- Volume Counts
    count(event_id) as total_scans,
    sum(case when ai_flagged = true then 1 else 0 end) as total_ai_alerts,
    sum(is_reviewed::int) as total_reviewed_scans,
    sum(is_pending) as total_pending_scans,

    -- Confusion Matrix Aggregations
    sum(is_tp) as true_positives,
    sum(is_fp) as false_positives,
    sum(is_tn) as true_negatives,
    sum(is_fn) as false_negatives,

    -- ML Performance Metrics (%)
    round(
        case when (sum(is_tp) + sum(is_fp)) > 0 
             then (sum(is_tp)::double / (sum(is_tp) + sum(is_fp))) * 100.0 
             else null 
        end, 2
    ) as precision_pct,

    round(
        case when (sum(is_tp) + sum(is_fn)) > 0 
             then (sum(is_tp)::double / (sum(is_tp) + sum(is_fn))) * 100.0 
             else null 
        end, 2
    ) as recall_sensitivity_pct,

    round(
        case when (sum(is_tn) + sum(is_fp)) > 0 
             then (sum(is_tn)::double / (sum(is_tn) + sum(is_fp))) * 100.0 
             else null 
        end, 2
    ) as specificity_pct,

    round(
        case when (sum(is_fn) + sum(is_tp)) > 0 
             then (sum(is_fn)::double / (sum(is_fn) + sum(is_tp))) * 100.0 
             else null 
        end, 2
    ) as false_negative_rate_pct,

    round(
        case when (2 * sum(is_tp) + sum(is_fp) + sum(is_fn)) > 0 
             then (2.0 * sum(is_tp) / (2 * sum(is_tp) + sum(is_fp) + sum(is_fn))) * 100.0 
             else null 
        end, 2
    ) as f1_score_pct,

    -- Turnaround Time Statistics (Direct Record-Level Quantiles)
    round(avg(total_turnaround_minutes), 1) as avg_turnaround_minutes,
    quantile_cont(total_turnaround_minutes, 0.50) as p50_turnaround_minutes,
    quantile_cont(total_turnaround_minutes, 0.90) as p90_turnaround_minutes,
    quantile_cont(total_turnaround_minutes, 0.95) as p95_turnaround_minutes,

    -- SLA Operational Metrics
    sum(case when met_sla = true then 1 else 0 end) as total_sla_compliant,
    round(
        case when sum(is_reviewed::int) > 0 
             then (sum(case when met_sla = true then 1 else 0 end)::double / sum(is_reviewed::int)) * 100.0 
             else null 
        end, 2
    ) as sla_compliance_pct

from int_data
group by 
    hospital_site_id,
    modality,
    finding_type,
    clinical_priority,
    model_version