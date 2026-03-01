import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.exceptions import AppError
from app.services.lsp_service import LspService

router = APIRouter(tags=["lsp"])
logger = logging.getLogger("lsp-controller")
service = LspService()


@router.websocket("/ws/lsp")
async def lsp_proxy(websocket: WebSocket) -> None:
    await websocket.accept()
    session = await service.create_session()

    async def on_message(payload: dict) -> None:
        await websocket.send_text(json.dumps(payload))

    await session.start(on_message)

    try:
        while True:
            message = await websocket.receive_text()
            try:
                payload = json.loads(message)
            except json.JSONDecodeError:
                await websocket.send_text(json.dumps({"message": "invalid_json"}))
                continue
            await session.send(payload)
    except WebSocketDisconnect:
        logger.info("lsp_ws_disconnect")
    except AppError as exc:
        await websocket.send_text(json.dumps({"message": exc.message}))
    except Exception:
        logger.exception("lsp_ws_error")
    finally:
        await session.stop()
        service.release()
