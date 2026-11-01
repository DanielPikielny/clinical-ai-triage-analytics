
    

    create  table
      "clinical_warehouse"."main_marts"."fct_clinical_impact__dbt_tmp"
  
    
    as (
      WITH int_scans AS (
    SELECT * FROM "clinical_warehouse"."main_int_clinical"."int_clinical_turnaround"
)

SELECT
    hospital_site_id,
    modality,
    finding_type,
    clinical_priority,
    COUNT(event_id) AS total_scans,
    COUNT(CASE WHEN ai_flagged THEN 1 END) AS total_ai_alerts,
    COUNT(CASE WHEN ai_detection_classification = 'TRUE_POSITIVE' THEN 1 END) AS true_positives,
    COUNT(CASE WHEN ai_detection_classification = 'FALSE_POSITIVE' THEN 1 END) AS false_positives,
    
    -- Calculated Metrics
    ROUND(
        CAST(COUNT(CASE WHEN ai_detection_classification = 'TRUE_POSITIVE' THEN 1 END) AS DOUBLE) /
        NULLIF(COUNT(CASE WHEN ai_flagged THEN 1 END), 0) * 100, 2
    ) AS ai_precision_percentage,

    ROUND(AVG(scan_to_ai_minutes), 2) AS avg_ai_processing_minutes,
    ROUND(AVG(total_turnaround_minutes), 2) AS avg_turnaround_minutes,
    
    MEDIAN(total_turnaround_minutes) AS median_turnaround_minutes

FROM int_scans
GROUP BY
    hospital_site_id,
    modality,
    finding_type,
    clinical_priority
    );
    
  