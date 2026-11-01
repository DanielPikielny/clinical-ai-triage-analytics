import subprocess
import sys


def run_step(command, description):
    print(f"\nRunning Step: {description}...")
    result = subprocess.run(command, shell=True)
    if result.returncode != 0:
        print(f"Error during step: {description}")
        sys.exit(1)
    print(f"{description} completed successfully!")


if __name__ == "__main__":
    print("Starting End-to-End Clinical Analytics Pipeline...")
    run_step("python scripts/init_db.py", "Database Initialization")
    run_step(
        "python scripts/generate_synthetic_data.py",
        "Synthetic Data Generation",
    )
    run_step("dbt run --project-dir . --profiles-dir .", "dbt Model Execution")
    run_step("dbt test --project-dir . --profiles-dir .", "dbt Data Quality Tests")
    print("\nEntire Clinical Data Pipeline Executed Successfully!")