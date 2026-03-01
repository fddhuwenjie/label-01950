from typing import List

from sqlalchemy.orm import Session

from app.entities.dialect_entity import DialectEntity
from app.mappers.dialect_mapper import DialectMapper


class DialectService:
    def __init__(self, session: Session) -> None:
        self.mapper = DialectMapper(session)

    def list_dialects(self) -> List[DialectEntity]:
        return self.mapper.list_all()
