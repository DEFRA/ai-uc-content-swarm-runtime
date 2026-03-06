from dataclasses import dataclass, field
from datetime import UTC, datetime


@dataclass
class UploadInitiation:
    upload_id: str


@dataclass
class ContextMetadata:
    """Metadata for a context document (file) attached to a run."""

    id: str  # fileId from uploader
    filename: str
    s3_key: str
    s3_bucket: str
    content_type: str
    checksum_sha256: str
    status: str = "uploaded"
    created_at: datetime = field(default_factory=lambda: datetime.now(tz=UTC))
