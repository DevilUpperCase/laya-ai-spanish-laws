from dataclasses import dataclass, field
from datetime import date
from typing import Protocol


@dataclass(frozen=True)
class PublicationRef:
    source_id: str
    external_id: str
    official_url: str
    publication_date: date


@dataclass(frozen=True)
class RawPublication:
    ref: PublicationRef
    content: bytes
    format: str = "xml"


@dataclass(frozen=True)
class SectionVersion:
    id: str
    section_key: str
    heading: str
    ordinal: int
    version_ref: str
    publication_date: date
    consolidation_date: date
    effective_from: date | None
    text: str
    sha256: str
    language_code: str = "es"
    effectiveness_verified: bool = False
    source_order: int = 0
    official_url: str | None = None


@dataclass(frozen=True)
class ParsedPublication:
    external_id: str
    title: str
    legal_type: str
    publication_date: date
    official_reference: str
    official_url: str
    eli: str | None
    scope: str
    issuer: str
    source_updated_at: str | None
    versions: tuple[SectionVersion, ...]
    relationships: tuple[tuple[str, str], ...] = ()
    is_consolidated: bool = True
    ingestion_warnings: tuple[str,...] = ()
    instrument_id: str | None = None


@dataclass(frozen=True)
class DiscoveryPage:
    publications: tuple[PublicationRef, ...]
    next_cursor: dict | None
    reported_total: int | None = None


@dataclass(frozen=True)
class ReconciliationReport:
    expected: int | None
    discovered: int
    integrated: int
    complete: bool
    gaps: tuple[str, ...]


class SourceAdapter(Protocol):
    source_id: str
    def discover(self, start_date: date | None, end_date: date | None, cursor: dict | None) -> DiscoveryPage: ...
    def fetch(self, ref: PublicationRef) -> RawPublication: ...
    def parse(self, raw: RawPublication) -> ParsedPublication: ...
