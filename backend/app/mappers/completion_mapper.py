from typing import List

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.entities.completion_entity import CompletionEntity


class CompletionMapper:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_by_dialect(self, dialect: str, workspace_id: int | None) -> List[CompletionEntity]:
        statement = select(CompletionEntity).where(CompletionEntity.dialect == dialect)
        if workspace_id is not None:
            statement = statement.where(
                (CompletionEntity.workspace_id == workspace_id)
                | (CompletionEntity.workspace_id.is_(None))
            )
        else:
            statement = statement.where(CompletionEntity.workspace_id.is_(None))
        return list(self.session.scalars(statement))

    def create(
        self, category: str, value: str, dialect: str, workspace_id: int | None
    ) -> CompletionEntity:
        entity = CompletionEntity(
            category=category,
            value=value,
            dialect=dialect,
            workspace_id=workspace_id,
        )
        self.session.add(entity)
        self.session.flush()
        return entity
