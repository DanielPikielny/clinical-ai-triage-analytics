
    
    

with all_values as (

    select
        ai_detection_classification as value_field,
        count(*) as n_records

    from "clinical_warehouse"."main_int_clinical"."int_clinical_turnaround"
    group by ai_detection_classification

)

select *
from all_values
where value_field not in (
    'TRUE_POSITIVE','FALSE_POSITIVE','FALSE_NEGATIVE','TRUE_NEGATIVE'
)


