"""Tests for PHI redaction."""

from app.middleware.phi_redaction import redact_phi


def test_redacts_ssn():
    """Should redact Social Security Numbers."""
    text = "Patient SSN is 123-45-6789"
    result = redact_phi(text)
    assert "123-45-6789" not in result
    assert "[REDACTED_SSN]" in result


def test_redacts_phone():
    """Should redact phone numbers."""
    text = "Contact at 555-123-4567"
    result = redact_phi(text)
    assert "555-123-4567" not in result
    assert "[REDACTED_PHONE]" in result


def test_redacts_mrn():
    """Should redact Medical Record Numbers."""
    text = "MRN: 12345678"
    result = redact_phi(text)
    assert "MRN: 12345678" not in result
    assert "[REDACTED_MRN]" in result


def test_preserves_medical_content():
    """Should not redact medical terminology."""
    text = "AHI: 3.2 events/hour. sleep score: 85/100. CPAP therapy."
    result = redact_phi(text)
    assert "AHI" in result
    assert "sleep score" in result
    assert "CPAP" in result


def test_redacts_date_of_birth():
    """Should redact dates that look like DOBs."""
    text = "DOB: 01/15/1985"
    result = redact_phi(text)
    assert "01/15/1985" not in result
    assert "[REDACTED_DOB]" in result
