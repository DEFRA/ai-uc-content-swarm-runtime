import uuid

import pydantic


class RunContextDocument(pydantic.BaseModel):
    """Context document at the swarm domain boundary."""

    id: uuid.UUID = pydantic.Field(
        ..., description="Unique identifier for the context document"
    )
    name: str = pydantic.Field(..., description="Name or title of the context document")
    description: str = pydantic.Field(
        ..., description="Description of the context document"
    )
    path: str = pydantic.Field(
        ..., description="Object path for retrieving the document content"
    )


class RunRequest(pydantic.BaseModel):
    task: str
    id: str = pydantic.Field(..., description="Unique identifier for the run")
    name: str = pydantic.Field(..., description="Name for the run")
    context_documents: list[RunContextDocument] = pydantic.Field(default_factory=list)


class RunResponse(pydantic.BaseModel):
    output: str
