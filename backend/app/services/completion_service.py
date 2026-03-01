import logging
from typing import List

from sqlalchemy.orm import Session

from app.entities.completion_entity import CompletionEntity
from app.mappers.completion_mapper import CompletionMapper

logger = logging.getLogger("completion-service")


class CompletionService:
    def __init__(self, session: Session) -> None:
        self.mapper = CompletionMapper(session)

    def list_completions(self, dialect: str, workspace_id: int | None) -> List[CompletionEntity]:
        return self.mapper.list_by_dialect(dialect=dialect, workspace_id=workspace_id)

    def create_completion(
        self, category: str, value: str, dialect: str, workspace_id: int | None
    ) -> CompletionEntity:
        entity = self.mapper.create(
            category=category, value=value, dialect=dialect, workspace_id=workspace_id
        )
        logger.info(
            "completion_created id=%s category=%s value=%s dialect=%s workspace_id=%s",
            entity.id,
            category,
            value,
            dialect,
            workspace_id,
        )
        return entity
