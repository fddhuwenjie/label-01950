from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers.deps import get_session
from app.schemas.workspace_schema import WorkspaceCreateRequest, WorkspaceUpdateRequest, WorkspaceResponse
from app.services.workspace_service import WorkspaceService

router = APIRouter(prefix="/api/workspaces", tags=["workspaces"])


@router.get("", response_model=List[WorkspaceResponse])
def list_workspaces(session: Session = Depends(get_session)) -> List[WorkspaceResponse]:
    service = WorkspaceService(session)
    return [
        WorkspaceResponse(id=entity.id, name=entity.name, dialect=entity.dialect)
        for entity in service.list_workspaces()
    ]


@router.post("", response_model=WorkspaceResponse)
def create_workspace(
    request: WorkspaceCreateRequest, session: Session = Depends(get_session)
) -> WorkspaceResponse:
    service = WorkspaceService(session)
    entity = service.create_workspace(name=request.name, dialect=request.dialect)
    return WorkspaceResponse(id=entity.id, name=entity.name, dialect=entity.dialect)


@router.put("/{workspace_id}", response_model=WorkspaceResponse)
def update_workspace(
    workspace_id: int, request: WorkspaceUpdateRequest, session: Session = Depends(get_session)
) -> WorkspaceResponse:
    service = WorkspaceService(session)
    entity = service.update_workspace(workspace_id, name=request.name, dialect=request.dialect)
    return WorkspaceResponse(id=entity.id, name=entity.name, dialect=entity.dialect)


@router.delete("/{workspace_id}")
def delete_workspace(workspace_id: int, session: Session = Depends(get_session)) -> None:
    service = WorkspaceService(session)
    service.delete_workspace(workspace_id)
