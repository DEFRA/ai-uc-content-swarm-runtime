from datetime import datetime

import pydantic


class ContextUploadRequest(pydantic.BaseModel):
    redirect: str | None = None


class CdpUploaderInitiateResponse(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="allow", populate_by_name=True)

    upload_id: str = pydantic.Field(..., alias="uploadId")


class FileUploadDetail(pydantic.BaseModel):
    """Details of a single uploaded file from the CDP uploader callback."""

    model_config = pydantic.ConfigDict(extra="allow", populate_by_name=True)

    file_id: str = pydantic.Field(..., alias="fileId")
    filename: str
    content_type: str = pydantic.Field(..., alias="contentType")
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

    id: str = pydantic.Field(
        ..., description="Unique identifier for the context (fileId)"
    )
    filename: str = pydantic.Field(..., description="Filename of the uploaded content")
    s3_key: str = pydantic.Field(
        ..., description="S3 object key for the uploaded content"
    )
    s3_bucket: str = pydantic.Field(..., description="S3 bucket containing the file")
    content_type: str = pydantic.Field(..., description="Content type of the file")
    checksum_sha256: str = pydantic.Field(
        ..., description="SHA256 checksum of the file"
    )
    status: str = pydantic.Field(
        default="uploaded", description="Status of the context document"
    )
    created_at: datetime = pydantic.Field(
        ..., description="When the context was created"
    )
