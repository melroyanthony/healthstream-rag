"""Tests for guardrails pipeline."""

from app.guardrails.pipeline import apply_guardrails


def test_redacts_ssn_in_response():
    """Should redact SSN patterns in LLM output."""
    response = "Your SSN is 123-45-6789"
    cleaned, passed = apply_guardrails(response, ["context"])
    assert "123-45-6789" not in cleaned


def test_blocks_medication_dosage_advice():
    """Should block responses containing medication dosage advice."""
    response = "I recommend a medication dosage of 500mg twice daily."
    cleaned, passed = apply_guardrails(response, ["medication dosage"])
    assert "cannot provide medical advice" in cleaned.lower()


def test_passes_factual_health_data():
    """Should pass through factual health data responses."""
    context = ["sleep score 85 therapy hours 7.2 AHI 3.2"]
    response = "Your sleep score was 85 with 7.2 therapy hours and AHI of 3.2"
    cleaned, passed = apply_guardrails(response, context)
    assert "sleep score" in cleaned


def test_blocks_diagnosis_advice():
    """Should block responses containing diagnosis."""
    response = "Based on symptoms, my differential diagnosis is pneumonia."
    cleaned, passed = apply_guardrails(response, ["differential diagnosis symptoms"])
    assert "cannot provide medical advice" in cleaned.lower()
