import logging
from typing import List

from sqlalchemy.orm import Session

from app.core.exceptions import AppError
from app.entities.workspace_entity import WorkspaceEntity
from app.mappers.workspace_mapper import WorkspaceMapper

logger = logging.getLogger("workspace-service")


class WorkspaceService:
    def __init__(self, session: Session) -> None:
        self.mapper = WorkspaceMapper(session)

    def list_workspaces(self) -> List[WorkspaceEntity]:
        return self.mapper.list_all()

    def create_workspace(self, name: str, dialect: str) -> WorkspaceEntity:
        entity = self.mapper.create(name=name, dialect=dialect)
        logger.info("workspace_created id=%s name=%s dialect=%s", entity.id, name, dialect)
        return entity

    def update_workspace(self, workspace_id: int, name: str, dialect: str) -> WorkspaceEntity:
        entity = self.mapper.get(workspace_id)
        if not entity:
            raise AppError("workspace_not_found", status_code=404)
        entity = self.mapper.update(entity, name=name, dialect=dialect)
        logger.info("workspace_updated id=%s name=%s dialect=%s", entity.id, name, dialect)
        return entity

    def delete_workspace(self, workspace_id: int) -> None:
        entity = self.mapper.get(workspace_id)
        if not entity:
            raise AppError("workspace_not_found", status_code=404)
        self.mapper.delete(entity)
        logger.info("workspace_deleted id=%s name=%s", entity.id, entity.name)
