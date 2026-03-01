from pydantic import BaseModel, Field


class CompletionQuery(BaseModel):
    dialect: str = Field(min_length=2, max_length=64)
    workspace_id: int | None = None


class CompletionCreateRequest(BaseModel):
    category: str = Field(min_length=2, max_length=32)
    value: str = Field(min_length=1, max_length=128)
    dialect: str = Field(min_length=2, max_length=64)
    workspace_id: int | None = None


class CompletionResponse(BaseModel):
    id: int
    category: str
    value: str
    dialect: str
    workspace_id: int | None
