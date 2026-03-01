from pydantic import BaseModel


class DialectResponse(BaseModel):
    id: int
    code: str
    label: str
