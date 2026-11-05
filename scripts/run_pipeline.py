import argparse
import subprocess
import sys


def run_command(cmd):
    print(f"\n--- Running: {cmd} ---")
    result = subprocess.run(cmd, shell=True)
    if result.returncode != 0:
        print(f"Command failed: {cmd}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Master Orchestrator Pipeline")
    parser.add_argument("--scenario", type=str, default="model_degradation")
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args()

    py_exe = sys.executable

    # 1. Infrastructure Initialization
    run_command(f'"{py_exe}" scripts/init_db.py')

    # 2. Synthetic Data Seeding & Event Stream Simulation
    run_command(f'"{py_exe}" scripts/generate_synthetic_data.py --scenario {args.scenario} --seed {args.seed}')
    run_command(f'"{py_exe}" scripts/stream_producer.py')

    # 3. Incremental dbt Transformations (with full-refresh on pipeline reset) & Tests
    run_command(f'"{py_exe}" -m dbt.cli.main run --project-dir . --profiles-dir . --full-refresh')
    run_command(f'"{py_exe}" -m dbt.cli.main test --project-dir . --profiles-dir .')

    # 4. Alerting & Statistical Drift Detection
    run_command(f'"{py_exe}" scripts/check_sla_alerts.py')
    run_command(f'"{py_exe}" scripts/detect_model_drift.py')
    run_command(f'"{py_exe}" scripts/compare_model_versions.py')

    # 5. Automated Pytest Test Suite
    run_command(f'"{py_exe}" -m pytest tests/')

    print("\n✓ End-to-End Pipeline Execution Completed Successfully!")


if __name__ == "__main__":
    main()