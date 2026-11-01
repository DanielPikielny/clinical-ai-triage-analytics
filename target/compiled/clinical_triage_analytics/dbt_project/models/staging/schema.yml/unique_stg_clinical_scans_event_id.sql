
    
    

select
    event_id as unique_field,
    count(*) as n_records

from "clinical_warehouse"."main_stg_clinical"."stg_clinical_scans"
where event_id is not null
group by event_id
having count(*) > 1


