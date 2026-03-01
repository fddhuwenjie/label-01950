from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.controllers.deps import get_session
from app.schemas.dialect_schema import DialectResponse
from app.services.dialect_service import DialectService

router = APIRouter(prefix="/api/dialects", tags=["dialects"])


@router.get("", response_model=List[DialectResponse])
def list_dialects(session: Session = Depends(get_session)) -> List[DialectResponse]:
    service = DialectService(session)
    return [
        DialectResponse(id=item.id, code=item.code, label=item.label)
        for item in service.list_dialects()
    ]
