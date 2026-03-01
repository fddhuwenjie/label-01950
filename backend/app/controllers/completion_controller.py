from typing import List

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.controllers.deps import get_session
from app.schemas.completion_schema import CompletionCreateRequest, CompletionResponse
from app.services.completion_service import CompletionService

router = APIRouter(prefix="/api/completions", tags=["completions"])


@router.get("", response_model=List[CompletionResponse])
def list_completions(
    dialect: str = Query(min_length=2, max_length=64),
    workspace_id: int | None = None,
    session: Session = Depends(get_session),
) -> List[CompletionResponse]:
    service = CompletionService(session)
    items = service.list_completions(dialect=dialect, workspace_id=workspace_id)
    return [
        CompletionResponse(
            id=item.id,
            category=item.category,
            value=item.value,
            dialect=item.dialect,
            workspace_id=item.workspace_id,
        )
        for item in items
    ]


@router.post("", response_model=CompletionResponse)
def create_completion(
    request: CompletionCreateRequest, session: Session = Depends(get_session)
) -> CompletionResponse:
    service = CompletionService(session)
    entity = service.create_completion(
        category=request.category,
        value=request.value,
        dialect=request.dialect,
        workspace_id=request.workspace_id,
    )
    return CompletionResponse(
        id=entity.id,
        category=entity.category,
        value=entity.value,
        dialect=entity.dialect,
        workspace_id=entity.workspace_id,
    )
