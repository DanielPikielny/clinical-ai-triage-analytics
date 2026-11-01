import os
import duckdb

# Ensure data folder exists
os.makedirs("data", exist_ok=True)

db_path = "data/clinical_warehouse.duckdb"

print(f"Initializing DuckDB at {db_path}...")
conn = duckdb.connect(db_path)

# Create organizational schemas inside DuckDB
schemas = ["raw_staging", "stg_clinical", "int_clinical", "marts"]
for schema in schemas:
    conn.execute(f"CREATE SCHEMA IF NOT EXISTS {schema};")
    print(f"  ✓ Created schema: {schema}")

conn.close()
print("Database initialized successfully!")