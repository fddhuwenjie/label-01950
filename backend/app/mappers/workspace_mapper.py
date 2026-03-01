from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.entities.workspace_entity import WorkspaceEntity


class WorkspaceMapper:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> List[WorkspaceEntity]:
        return list(self.session.scalars(select(WorkspaceEntity)))

    def get(self, workspace_id: int) -> Optional[WorkspaceEntity]:
        return self.session.get(WorkspaceEntity, workspace_id)

    def create(self, name: str, dialect: str) -> WorkspaceEntity:
        entity = WorkspaceEntity(name=name, dialect=dialect)
        self.session.add(entity)
        self.session.flush()
        return entity

    def update(self, entity: WorkspaceEntity, name: str, dialect: str) -> WorkspaceEntity:
        entity.name = name
        entity.dialect = dialect
        self.session.add(entity)
        self.session.flush()
        return entity

    def delete(self, entity: WorkspaceEntity) -> None:
        self.session.delete(entity)
