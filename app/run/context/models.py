import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class UploadInitiation:
    upload_id: str


@dataclass
class CdpUploaderMetadata:
    """Metadata for CDP uploader integration (S3 upload tracking)."""

    s3_bucket: str
    upload_id: str | None = None
    s3_key: str | None = None
    checksum_sha256: str | None = None
    filename: str | None = None
    status: str = "pending"


@dataclass
class ContextMetadata:
    """Metadata for a context document (file) attached to a run."""

    id: uuid.UUID
    title: str
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    description: str | None = None
    cdp_uploader: CdpUploaderMetadata | None = None
