# Clinical AI Triage & Operational Analytics Pipeline

An end-to-end analytics engineering pipeline designed to ingest, transform, test, and visualize the clinical impact and operational metrics of real-time AI radiology triage systems across multi-site hospital networks.

---

##  System Architecture & Data Lineage

```text
[ Raw DICOM / AI Event Logs ] 
             │
             ▼
    [ DuckDB Warehouse ] (raw_staging.raw_ai_scans)
             │
             ▼
   [ dbt Staging Layer ] (stg_clinical_scans) ➔ Cleansing, Type Casts & Interval Prep
             │
             ▼
[ dbt Intermediate Layer ] (int_clinical_turnaround) ➔ AI Classification & SLA Bucketing
             │
             ▼
     [ dbt Marts Layer ] (fct_clinical_impact) ➔ Aggregated Clinical KPIs
             │
      ┌──────┴────────────────┐
      ▼                       ▼
[ Streamlit Dashboard ]   [ Python SLA Alert Monitor ]

---

##  Tech Stack & Frameworks

* **Data Warehouse:** [DuckDB](https://duckdb.org/) (Zero-copy fast analytical engine)
* **Transformation & Modeling:** [dbt-core](https://www.getdbt.com/) / `dbt-duckdb`
* **Data Ingestion & Orchestration:** Python 3.10+, Pandas, Faker
* **Visualization & Reporting:** Streamlit
* **Data Quality & CI/CD:** dbt test suite (7 generic + custom singular SQL assertions), GitHub Actions

---

##  Quick Start Guide

### 1. Prerequisites & Environment Setup
Clone the repository and set up a Python virtual environment:
```powershell
# Clone repo
git clone [https://github.com/your-username/clinical-ai-triage-analytics.git](https://github.com/your-username/clinical-ai-triage-analytics.git)
cd clinical-ai-triage-analytics

# Create & activate venv
python -m venv venv
.\venv\Scripts\activate   # Windows PowerShell
# source venv/bin/activate # macOS/Linux

# Install dependencies
pip install duckdb dbt-duckdb pandas faker streamlit