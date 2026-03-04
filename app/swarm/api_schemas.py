import pydantic


class RunRequest(pydantic.BaseModel):
    task: str


class RunResponse(pydantic.BaseModel):
    output: str
