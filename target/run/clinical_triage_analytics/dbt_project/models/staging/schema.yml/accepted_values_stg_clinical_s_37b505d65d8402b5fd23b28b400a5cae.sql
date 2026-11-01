
    
    select
      count(*) as failures,
      count(*) != 0 as should_warn,
      count(*) != 0 as should_error
    from (
      
    
  
    
    

with all_values as (

    select
        clinical_priority as value_field,
        count(*) as n_records

    from "clinical_warehouse"."main_stg_clinical"."stg_clinical_scans"
    group by clinical_priority

)

select *
from all_values
where value_field not in (
    'EMERGENCY','URGENT','ROUTINE'
)



  
  
      
    ) dbt_internal_test