"""HealthKit / Health Connect data loader.

Normalizes Apple HealthKit and Google Health Connect data
into documents for the RAG pipeline.

Data types: sleep sessions, AHI, mask seal, therapy hours,
sleep scores, device events.

Production: receives events via Kinesis Data Streams.
Demo: accepts HealthKit-format JSON directly.
"""

from app.loaders.base import BaseDataLoader, LoadedDocument, register_loader


@register_loader("healthkit")
class HealthKitLoader(BaseDataLoader):
    """Loader for Apple HealthKit / Google Health Connect data."""

    @property
    def source_type(self) -> str:
        return "healthkit"

    def load(self, raw_data: dict) -> list[LoadedDocument]:
        """Parse HealthKit session data into documents.

        Expected format:
        {
            "sessions": [
                {
                    "date": "2026-03-22",
                    "sleep_score": 88,
                    "therapy_hours": 7.5,
                    "ahi": 2.8,
                    "mask_seal": "Good",
                    "leak_rate": 3.2,
                    "device": "AutoSet CPAP"
                }
            ]
        }
        """
        documents = []
        for session in raw_data.get("sessions", []):
            date = session.get("date", "unknown")
            parts = [f"Sleep session {date}:"]

            if "sleep_score" in session:
                parts.append(f"sleep score {session['sleep_score']} out of 100.")
            if "therapy_hours" in session:
                parts.append(f"Therapy hours {session['therapy_hours']}.")
            if "ahi" in session:
                parts.append(f"AHI {session['ahi']} events per hour.")
            if "mask_seal" in session:
                parts.append(f"Mask seal: {session['mask_seal']}.")
            if "leak_rate" in session:
                parts.append(f"Leak rate: {session['leak_rate']} L/min.")
            if "device" in session:
                parts.append(f"Device: {session['device']}.")

            documents.append(
                LoadedDocument(
                    text=" ".join(parts),
                    source_type="healthkit",
                    source_id=f"sleep-session-{date}",
                    metadata={"date": date},
                )
            )

        return documents
