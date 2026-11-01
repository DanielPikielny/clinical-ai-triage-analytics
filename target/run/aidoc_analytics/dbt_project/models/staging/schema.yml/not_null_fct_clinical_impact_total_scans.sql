
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    



select total_scans
from "clinical_warehouse"."main_marts"."fct_clinical_impact"
where total_scans is null



  
  
      
    ) dbt_internal_test