import uuid
from datetime import datetime

import pydantic
import pydantic.alias_generators


class ContextUploadRequest(pydantic.BaseModel):
    title: str
    description: str | None = None
    redirect: str


class CdpUploaderInitiateResponse(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(
        populate_by_name=True, alias_generator=pydantic.alias_generators.to_camel
    )

    upload_id: str = pydantic.Field(
        ...,
        alias="uploadId",
        description="Unique identifier for the initiated upload session",
    )


class FileUploadDetail(pydantic.BaseModel):
    """Details of a single uploaded file from the CDP uploader callback."""

    model_config = pydantic.ConfigDict(extra="allow", populate_by_name=True)

    file_id: str = pydantic.Field(..., alias="fileId")
    filename: str
    file_status: str = pydantic.Field(..., alias="fileStatus")
    content_length: int = pydantic.Field(..., alias="contentLength")
    checksum_sha256: str = pydantic.Field(..., alias="checksumSha256")
    detected_content_type: str | None = pydantic.Field(
        None, alias="detectedContentType"
    )
    s3_key: str = pydantic.Field(..., alias="s3Key")
    s3_bucket: str = pydantic.Field(..., alias="s3Bucket")


class CdpUploaderStatusPayload(pydantic.BaseModel):
    """Callback payload from the CDP uploader service."""

    model_config = pydantic.ConfigDict(extra="allow", populate_by_name=True)

    upload_status: str = pydantic.Field(..., alias="uploadStatus")
    metadata: dict = pydantic.Field(default_factory=dict)
    form: dict[str, FileUploadDetail | str] = pydantic.Field(default_factory=dict)
    number_of_rejected_files: int = pydantic.Field(
        default=0, alias="numberOfRejectedFiles"
    )


class ContextResponse(pydantic.BaseModel):
    """Response model for a context document attached to a run."""

    model_config = pydantic.ConfigDict(
        populate_by_name=True, alias_generator=pydantic.alias_generators.to_camel
    )

    id: uuid.UUID = pydantic.Field(
        ..., description="Unique identifier for the context (fileId)"
    )
    filename: str | None = pydantic.Field(
        default=None, description="Filename of the uploaded content"
    )
    title: str = pydantic.Field(..., description="Title of the context document")
    s3_key: str | None = pydantic.Field(
        None, description="S3 object key for the uploaded content"
    )
    s3_bucket: str = pydantic.Field(..., description="S3 bucket containing the file")
    checksum_sha256: str | None = pydantic.Field(
        None, description="SHA256 checksum of the file"
    )
    status: str = pydantic.Field(
        default="uploaded", description="Status of the context document"
    )
    created_at: datetime = pydantic.Field(
        ..., description="When the context was created"
    )
