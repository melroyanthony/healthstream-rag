"""FHIR R4 data loader.

Parses FHIR R4 Bundle resources into documents for the RAG pipeline.
Supports: Patient, Observation, Condition, MedicationRequest, CarePlan.

Production: receives events via AWS HealthLake + EventBridge.
Demo: accepts FHIR-format JSON directly.
"""

from app.loaders.base import BaseDataLoader, LoadedDocument, register_loader

# FHIR resource type → text extraction logic
RESOURCE_PARSERS = {
    "Condition": "_parse_condition",
    "MedicationRequest": "_parse_medication",
    "CarePlan": "_parse_care_plan",
    "Observation": "_parse_observation",
}


@register_loader("fhir")
class FHIRLoader(BaseDataLoader):
    """Loader for FHIR R4 Bundle resources."""

    @property
    def source_type(self) -> str:
        return "fhir"

    def load(self, raw_data: dict) -> list[LoadedDocument]:
        """Parse FHIR Bundle or individual resources.

        Expected format (Bundle):
        {
            "resourceType": "Bundle",
            "entry": [
                {"resource": {"resourceType": "Condition", ...}},
                {"resource": {"resourceType": "MedicationRequest", ...}}
            ]
        }

        Or single resource:
        {"resourceType": "Condition", "code": {...}, ...}
        """
        if raw_data.get("resourceType") == "Bundle":
            resources = [
                entry["resource"]
                for entry in raw_data.get("entry", [])
                if "resource" in entry
            ]
        else:
            resources = [raw_data]

        documents = []
        for resource in resources:
            resource_type = resource.get("resourceType", "Unknown")
            parser_name = RESOURCE_PARSERS.get(resource_type)

            if parser_name and hasattr(self, parser_name):
                text = getattr(self, parser_name)(resource)
            else:
                text = f"FHIR {resource_type}: {_flatten_resource(resource)}"

            resource_id = resource.get("id", resource_type.lower())
            documents.append(
                LoadedDocument(
                    text=text,
                    source_type="fhir",
                    source_id=f"{resource_type}/{resource_id}",
                    metadata={"resource_type": resource_type},
                )
            )

        return documents

    def _parse_condition(self, resource: dict) -> str:
        code = resource.get("code", {})
        codings = code.get("coding", [])
        coding = codings[0] if codings else {}
        display = coding.get("display", code.get("text", "Unknown condition"))
        icd_code = coding.get("code", "")
        clinical_codings = resource.get("clinicalStatus", {}).get("coding", [])
        status = clinical_codings[0].get("code", "unknown") if clinical_codings else "unknown"
        severity = resource.get("severity", {}).get("text", "")

        parts = [f"FHIR Condition: {display}"]
        if icd_code:
            parts.append(f"ICD-10 {icd_code}.")
        parts.append(f"Status: {status}.")
        if severity:
            parts.append(f"Severity: {severity}.")
        return " ".join(parts)

    def _parse_medication(self, resource: dict) -> str:
        med = resource.get("medicationCodeableConcept", {})
        med_codings = med.get("coding", [])
        fallback = med_codings[0].get("display", "Unknown") if med_codings else "Unknown"
        display = med.get("text", fallback)
        status = resource.get("status", "unknown")
        return f"FHIR MedicationRequest: {display}. Status: {status}."

    def _parse_care_plan(self, resource: dict) -> str:
        title = resource.get("title", resource.get("description", "Care plan"))
        status = resource.get("status", "unknown")
        goals = [
            g.get("display", str(g))
            for g in resource.get("goal", [])
        ]
        parts = [f"FHIR CarePlan: {title}. Status: {status}."]
        if goals:
            parts.append(f"Goals: {', '.join(goals)}.")
        return " ".join(parts)

    def _parse_observation(self, resource: dict) -> str:
        code = resource.get("code", {}).get("text", "Observation")
        value = resource.get("valueQuantity", {})
        val_str = f"{value.get('value', '')} {value.get('unit', '')}".strip()
        if val_str:
            return f"FHIR Observation: {code}. Value: {val_str}."
        return f"FHIR Observation: {code}."


def _flatten_resource(resource: dict) -> str:
    """Simple flattening of FHIR resource to text."""
    parts = []
    for key, value in resource.items():
        if key in ("resourceType", "id", "meta"):
            continue
        if isinstance(value, str):
            parts.append(f"{key}: {value}")
        elif isinstance(value, (int, float)):
            parts.append(f"{key}: {value}")
    return ". ".join(parts) if parts else str(resource)
