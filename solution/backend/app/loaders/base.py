"""Base data loader interface — Cognita-inspired registry pattern.

Each loader normalizes data from a specific source format
into documents ready for the ingest pipeline.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass

# Global loader registry — components self-register
LOADER_REGISTRY: dict[str, type["BaseDataLoader"]] = {}


def register_loader(source_type: str):
    """Decorator to register a data loader for a source type."""
    def decorator(cls):
        if source_type in LOADER_REGISTRY:
            raise ValueError(
                f"Loader already registered for '{source_type}': "
                f"{LOADER_REGISTRY[source_type].__name__}"
            )
        LOADER_REGISTRY[source_type] = cls
        return cls
    return decorator


def get_loader(source_type: str) -> "BaseDataLoader":
    """Get the loader instance for a given source type."""
    if source_type not in LOADER_REGISTRY:
        raise ValueError(
            f"No loader registered for '{source_type}'. "
            f"Available: {list(LOADER_REGISTRY.keys())}"
        )
    return LOADER_REGISTRY[source_type]()


@dataclass
class LoadedDocument:
    """A document ready for the ingest pipeline."""
    text: str
    source_type: str
    source_id: str
    metadata: dict | None = None


class BaseDataLoader(ABC):
    """Abstract data loader — normalizes source-specific data into documents."""

    @abstractmethod
    def load(self, raw_data: dict) -> list[LoadedDocument]:
        """Parse raw source data into normalized documents.

        Args:
            raw_data: Source-specific data (HealthKit JSON, FHIR Bundle, HL7v2, etc.)

        Returns:
            List of normalized documents ready for PHI redaction + embedding.
        """

    @property
    @abstractmethod
    def source_type(self) -> str:
        """The source type this loader handles."""
