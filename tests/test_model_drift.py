import numpy as np
import pytest
from scripts.detect_model_drift import calculate_psi


def test_psi_identical_distributions():
    # Identical distributions should yield a PSI near 0.0
    baseline = np.random.uniform(0.1, 0.9, 500)
    target = baseline.copy()

    psi = calculate_psi(baseline, target)
    assert psi < 0.05, f"Expected PSI < 0.05 for identical distributions, got {psi}"


def test_psi_significant_drift():
    # Drastically shifted distribution should trigger critical drift (PSI >= 0.25)
    baseline = np.random.beta(2, 8, 500)  # Skewed low
    target = np.random.beta(8, 2, 500)  # Skewed high

    psi = calculate_psi(baseline, target)
    assert (
        psi >= 0.25
    ), f"Expected PSI >= 0.25 for shifted distribution, got {psi}"


def test_expected_calibration_error_calculation():
    # Test ECE calculation on perfectly calibrated dummy array
    confidences = np.array([0.9, 0.8, 0.7, 0.6])
    accuracies = np.array([0.9, 0.8, 0.7, 0.6])
    counts = np.array([100, 100, 100, 100])

    total_samples = counts.sum()
    ece = (
        (counts / total_samples) * np.abs(confidences - accuracies)
    ).sum() * 100.0

    assert ece == 0.0, f"Expected ECE of 0.0% for perfect calibration, got {ece}"