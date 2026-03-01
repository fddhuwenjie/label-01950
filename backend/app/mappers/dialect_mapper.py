from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.entities.dialect_entity import DialectEntity


class DialectMapper:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> List[DialectEntity]:
        return list(self.session.scalars(select(DialectEntity)))
