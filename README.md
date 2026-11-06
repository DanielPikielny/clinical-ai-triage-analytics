# Clinical AI Triage & Model Observability Platform

An enterprise-grade, end-to-end AI Observability and Model Monitoring Platform for Radiology AI Triage workflows. 

The platform tracks operational turnaround times (TAT tail-latency quantiles p50, p90, p95), monitors ML model performance degradation (Precision, Recall / Sensitivity, Specificity, F1-Score, FNR), detects population distribution shifts (Population Stability Index - PSI), evaluates model probability calibration (Expected Calibration Error - ECE), and manages stateful alert lifecycles using persistent DuckDB storage and dbt transformations.

---

## System Architecture

```
                                  [ DICOM Event Stream / Synthetic Generator ]
                                                       │
                                                       ▼
                                    ┌─────────────────────────────────────┐
                                    │  Defensive Micro-Batch Ingestion    │
                                    │      (scripts/ingest_events.py)     │
                                    └──────────────────┬──────────────────┘
                                                       │
                                                       ▼
                                    ┌─────────────────────────────────────┐
                                    │    DuckDB Data Warehouse Storage    │
                                    │   (data/clinical_warehouse.duckdb)  │
                                    └──────────────────┬──────────────────┘
                                                       │
                                                       ▼
                                    ┌─────────────────────────────────────┐
                                    │       dbt Transformation Layer      │
                                    │  - stg_clinical_scans (Incremental) │
                                    │  - int_clinical_turnaround (View)   │
                                    │  - fct_clinical_impact (Mart Table) │
                                    └──────────────────┬──────────────────┘
                                                       │
           ┌───────────────────────────────────────────┼───────────────────────────────────────────┐
           ▼                                           ▼                                           ▼
┌─────────────────────┐                     ┌─────────────────────┐                     ┌─────────────────────┐
│ Stateful Alerting   │                     │ Statistical Drift   │                     │ Interactive UI      │
│  (check_sla_alerts) │                     │ (detect_model_drift)│                     │  (app/dashboard.py) │
│ - Fingerprint Hash  │                     │ - 10-Decile PSI     │                     │ - Record Quantiles  │
│ - ACTIVE/RESOLVED   │                     │ - fct_model_drift   │                     │ - ECE Reliability   │
└─────────────────────┘                     └─────────────────────┘                     └─────────────────────┘
```

---

## Key Features

* **Incremental Transformation & Data Quality:** Modular dbt SQL pipeline with a 3-day overlapping lookback window to capture delayed clinician reviews, protected by automated schema assertions (unique, not_null, accepted_values).
* **Record-Level Tail-Latency Quantiles:** Computes exact p50, p90, and p95 turnaround latency directly from record-level scan events rather than averaging group-level quantiles.
* **Stateful Anomaly Engine:** Configurable rule evaluation (config/alert_rules.yml) generating deterministic hash fingerprints (MD5 of Site + Finding + Priority + Metric + Version) to maintain active alert durations and automatic resolution updates (ACTIVE -> RESOLVED).
* **Statistical Model Drift (PSI):** Decile-binned Population Stability Index calculations tracking confidence distribution shifts between baseline reference windows and target operational windows (PSI >= 0.25 flags critical drift).
* **Probability Calibration (ECE):** Evaluates Expected Calibration Error and renders empirical reliability diagrams to verify model confidence scores against radiologist ground-truth confirmation rates.
* **Micro-Batch Event Stream Ingestion:** Asynchronous ingestion validator enforcing strict schema contracts, ISO-8601 timestamp validation, clinical priority boundaries, and confidence range constraints ([0.0, 1.0]).

---

## Project Structure

```
clinical-ai-triage-analytics/
├── app/
│   └── dashboard.py               # Interactive Streamlit Observability Platform UI
├── config/
│   └── alert_rules.yml            # Centralized threshold rules & priority SLA targets
├── dbt_project/
│   ├── dbt_project.yml            # dbt project configuration
│   ├── profiles.yml               # DuckDB connection profile
│   ├── models/
│   │   ├── staging/
│   │   │   ├── stg_clinical_scans.sql   # Incremental staging model
│   │   │   └── schema.yml              # Schema data quality assertions
│   │   ├── intermediate/
│   │   │   └── int_clinical_turnaround.sql  # Confusion matrix classification view
│   │   └── marts/
│   │       └── fct_clinical_impact.sql      # Site & finding KPI mart table
│   └── tests/
│       └── assert_review_after_scan.sql     # Singular dbt custom test
├── scripts/
│   ├── init_db.py                 # DuckDB schema initialization utility
│   ├── generate_synthetic_data.py # Realistic clinical matrix synthetic generator
│   ├── ingest_events.py           # Defensive micro-batch ingestion engine
│   ├── stream_producer.py         # Live streaming event generator
│   ├── check_sla_alerts.py        # Stateful alert fingerprinting engine
│   ├── detect_model_drift.py      # PSI distribution drift calculator
│   ├── compare_model_versions.py  # Model deployment impact analysis
│   └── run_pipeline.py            # Master orchestrator script
└── tests/
    ├── test_alert_rules.py        # Rule engine configuration tests
    ├── test_end_to_end.py         # E2E warehouse state & alert lifecycle tests
    ├── test_model_drift.py        # PSI & ECE mathematical unit tests
    └── test_stream_ingestion.py   # Ingestion payload validation tests
```

---

## Quickstart Guide

### 1. Prerequisites & Virtual Environment Setup

Ensure Python 3.10+ is installed on your system. Clone the repository and initialize a Python virtual environment:

```powershell
# Clone the repository
git clone https://github.com/barva/clinical-ai-triage-analytics.git
cd clinical-ai-triage-analytics

# Create and activate virtual environment (Windows PowerShell)
python -m venv venv
.\venv\Scripts\Activate.ps1

# Install project dependencies
pip install duckdb dbt-duckdb pandas numpy streamlit pytest pyyaml
```

---

### 2. Execute End-to-End Orchestrator Pipeline

Run the master orchestrator to initialize the DuckDB database, seed synthetic data under a degraded scenario, simulate live event streams, execute dbt models and data quality tests, run alert and drift engines, and launch the Pytest suite:

```powershell
python scripts/run_pipeline.py --scenario model_degradation --seed 42
```

#### Pipeline Execution Sequence:
1. **scripts/init_db.py**: Prepares schema namespaces (raw_staging, main_marts, main_stg_clinical).
2. **scripts/generate_synthetic_data.py**: Generates 2,000 realistic clinical records enforcing matrix pairing constraints (e.g., Pulmonary Embolism -> CT / Emergency).
3. **scripts/stream_producer.py**: Simulates live DICOM acquisition micro-batches with strict payload validation.
4. **dbt run --full-refresh & dbt test**: Compiles incremental models and verifies 7 generic/custom data assertions.
5. **scripts/check_sla_alerts.py**: Evaluates operational and model metrics against config/alert_rules.yml.
6. **scripts/detect_model_drift.py**: Calculates Population Stability Index (PSI) across 10 deciles per slice.
7. **pytest tests/**: Runs all 12 automated Python unit and integration tests.

---

### 3. Launch Interactive Streamlit Dashboard

To inspect real-time metrics, persistent alert lifecycle history, PSI distribution shifts, and calibration diagrams:

```powershell
python -m streamlit run app/dashboard.py
```

The UI will automatically open at `http://localhost:8501` featuring:
* **Slice Controls:** Filter by Hospital Site, Finding Type, and AI Model Version.
* **Headline Metrics:** Record-level p95 TAT latency, SLA compliance, precision, and recall.
* **Persistent Alert Audit:** Active vs. Resolved anomaly tracking with timestamps.
* **Statistical Model Drift:** Tabulated PSI score rankings per clinical slice.
* **Reliability Diagram:** ECE curve comparing confidence scores against radiologist confirmation.

---

### 4. Automated Testing Suite

To execute the unit and integration test suite independently:

```powershell
python -m pytest tests/
```

---

## Metric Definitions

| Metric | Formula / Logic | Clinical Significance |
| :--- | :--- | :--- |
| **Precision** | TP / (TP + FP) * 100 | Measures diagnostic accuracy; low precision causes clinician alert fatigue. |
| **Recall (Sensitivity)** | TP / (TP + FN) * 100 | Measures sensitivity; low recall leads to missed critical findings. |
| **False Negative Rate (FNR)** | FN / (TP + FN) * 100 | Proportion of true pathology missed by AI; primary safety metric. |
| **p95 Turnaround (TAT)** | 95th Percentile of (T_reviewed - T_scan) | Tail-latency outlier measurement for emergency queue bottlenecks. |
| **Population Stability Index (PSI)** | Sum( (P_i - Q_i) * ln(P_i / Q_i) ) | Quantifies confidence distribution shift (>= 0.25 flags critical drift). |
| **Expected Calibration Error (ECE)** | Sum( (|B_m| / N) * \|acc(B_m) - conf(B_m)\| ) | Evaluates whether model confidence reflects true probability of correctness. |

---

