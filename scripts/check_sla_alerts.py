import duckdb

DB_PATH = "data/clinical_warehouse.duckdb"

PRECISION_THRESHOLDS = {
    "Intracranial Hemorrhage": 75.0,
    "Pulmonary Embolism": 70.0,
    "Acute Ischemic Stroke": 75.0,
    "Cervical Spine Fracture": 65.0,
    "Pneumothorax": 65.0,
}

TAT_THRESHOLDS_MINS = {"EMERGENCY": 45.0, "URGENT": 120.0, "ROUTINE": 240.0}


def check_alerts():
    conn = duckdb.connect(DB_PATH)

    print("================================================")
    print("CLINICAL SLA & AI MODEL MONITORS RUNNING...")
    print("================================================\n")

    query = """
        SELECT 
            hospital_site_id, 
            modality,
            finding_type, 
            clinical_priority,
            total_scans,
            total_ai_alerts,
            ai_precision_percentage, 
            avg_turnaround_minutes
        FROM main_marts.fct_clinical_impact;
    """

    results = conn.execute(query).fetchall()
    precision_alerts = 0
    tat_alerts = 0

    for (
        site,
        modality,
        finding,
        priority,
        total_scans,
        alerts,
        precision,
        tat,
    ) in results:
        target_precision = PRECISION_THRESHOLDS.get(finding, 70.0)
        if precision is not None and precision < target_precision:
            print(
                f"[PRECISION BREACH] Site: {site} | Finding: {finding} ({modality})"
            )
            print(
                f"   ↳ Precision: {precision}% (Target: >={target_precision}% across {alerts} alerts)\n"
            )
            precision_alerts += 1

        target_tat = TAT_THRESHOLDS_MINS.get(priority, 180.0)
        if tat is not None and tat > target_tat:
            print(
                f"[TAT SLA BREACH] Site: {site} | Priority: {priority} ({finding})"
            )
            print(
                f"   ↳ Avg TAT: {tat} mins (Target: <={target_tat} mins across {total_scans} scans)\n"
            )
            tat_alerts += 1

    print("==================================================")
    print("SUMMARY OF CLINICAL MONITORING RESULTS:")
    print(f"  • Total Precision Alerts: {precision_alerts}")
    print(f"  • Total Turnaround SLA Breaches: {tat_alerts}")
    print("==================================================")

    conn.close()


if __name__ == "__main__":
    check_alerts()