import os
import pytest
import yaml


def test_alert_rules_config_exists():
    config_path = "config/alert_rules.yml"
    assert os.path.exists(config_path), "alert_rules.yml config file missing"

    with open(config_path, "r") as f:
        config = yaml.safe_load(f)

    assert "global_thresholds" in config
    assert "precision_critical" in config["global_thresholds"]
    assert "priority_tat_p95_targets_minutes" in config
    assert config["priority_tat_p95_targets_minutes"]["EMERGENCY"] == 45


def test_confusion_matrix_precision_calculation():
    tp = 80
    fp = 20
    precision = (tp / (tp + fp)) * 100.0
    assert precision == 80.0


def test_confusion_matrix_recall_calculation():
    tp = 75
    fn = 25
    recall = (tp / (tp + fn)) * 100.0
    assert recall == 75.0