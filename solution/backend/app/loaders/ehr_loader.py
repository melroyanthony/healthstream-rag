"""EHR / HL7v2 data loader.

Converts legacy EHR formats (HL7v2, CCD/CCDA) into documents
for the RAG pipeline by normalizing to FHIR R4 text.

Production: receives files via S3 Landing Zone + Lambda trigger.
Demo: accepts pre-parsed EHR records as JSON.
"""

from app.loaders.base import BaseDataLoader, LoadedDocument, register_loader


@register_loader("ehr")
class EHRLoader(BaseDataLoader):
    """Loader for legacy EHR data (HL7v2, CCD/CCDA)."""

    @property
    def source_type(self) -> str:
        return "ehr"

    def load(self, raw_data: dict) -> list[LoadedDocument]:
        """Parse EHR records into documents.

        Expected format:
        {
            "format": "hl7v2" | "ccda" | "text",
            "records": [
                {
                    "record_id": "EHR-001",
                    "record_type": "discharge_summary" | "lab_result" | "clinical_note",
                    "text": "Patient presented with...",
                    "date": "2026-01-15"
                }
            ]
        }

        In production, HL7v2 messages would be parsed by an HL7 parser
        (e.g., python-hl7) and CCDA would be parsed by an XML parser.
        For the demo, we accept pre-parsed text records.
        """
        source_format = raw_data.get("format", "text")
        documents = []

        for record in raw_data.get("records", []):
            record_id = record.get("record_id", "ehr-unknown")
            record_type = record.get("record_type", "clinical_note")
            text = record.get("text", "")
            date = record.get("date", "")

            if not text:
                continue

            # Normalize: prefix with record type for context
            normalized = f"EHR {record_type}"
            if date:
                normalized += f" ({date})"
            normalized += f": {text}"

            documents.append(
                LoadedDocument(
                    text=normalized,
                    source_type="ehr",
                    source_id=record_id,
                    metadata={
                        "record_type": record_type,
                        "original_format": source_format,
                        "date": date,
                    },
                )
            )

        return documents
