import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class UploadInitiation:
    upload_id: str


@dataclass
class ContextMetadata:
    """Metadata for a context document (file) attached to a run."""

    id: uuid.UUID
    title: str
    s3_key: str
    s3_bucket: str
    content_type: str
    checksum_sha256: str
    filename: str | None = None
    status: str = "uploaded"
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
    description: str | None = None
