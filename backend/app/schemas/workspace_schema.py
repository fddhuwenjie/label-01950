from pydantic import BaseModel, Field


class WorkspaceCreateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    dialect: str = Field(min_length=2, max_length=64)


class WorkspaceUpdateRequest(BaseModel):
    name: str = Field(min_length=2, max_length=128)
    dialect: str = Field(min_length=2, max_length=64)


class WorkspaceResponse(BaseModel):
    id: int
    name: str
    dialect: str
