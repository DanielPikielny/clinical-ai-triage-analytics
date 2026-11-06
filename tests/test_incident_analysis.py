import pytest
from scripts.analyze_incident import analyze_incident_root_cause


def test_analyze_incident_returns_valid_structure():
    # Execute root cause analysis without arguments (analyzes highest severity alert)
    result = analyze_incident_root_cause()

    assert isinstance(result, dict)
    assert "status" in result
    assert result["status"] in ["INCIDENT_ANALYZED", "NO_INCIDENT_FOUND"]

    if result["status"] == "INCIDENT_ANALYZED":
        assert "alert" in result
        assert "drift" in result
        assert "metrics" in result
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)
        assert len(result["recommendations"]) > 0


def test_analyze_incident_invalid_hash_handling():
    result = analyze_incident_root_cause(alert_hash="NON_EXISTENT_HASH_999")
    assert result["status"] == "NO_INCIDENT_FOUND"