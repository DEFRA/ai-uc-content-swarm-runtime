import pydantic


class ContextUploadRequest(pydantic.BaseModel):
    redirect: str | None = None


class CdpUploaderInitiateResponse(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="allow", populate_by_name=True)

    upload_id: str = pydantic.Field(..., alias="uploadId")


class CdpUploaderStatusResponse(pydantic.BaseModel):
    model_config = pydantic.ConfigDict(extra="allow")

    status: str
