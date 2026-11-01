
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select event_id
from "clinical_warehouse"."main_int_clinical"."int_clinical_turnaround"
where event_id is null



  
  
      
    ) dbt_internal_test