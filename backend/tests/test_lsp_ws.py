import json

from app.controllers import lsp_controller


class FakeSession:
    def __init__(self):
        self.callback = None

    async def start(self, on_message):
        self.callback = on_message

    async def send(self, payload):
        await self.callback({"id": payload.get("id"), "result": "ok"})

    async def stop(self):
        return None


class FakeService:
    async def create_session(self):
        return FakeSession()

    def release(self):
        return None


def test_lsp_websocket(client):
    lsp_controller.service = FakeService()
    with client.websocket_connect("/ws/lsp") as websocket:
        websocket.send_text(json.dumps({"id": 1, "method": "initialize"}))
        response = websocket.receive_text()
        payload = json.loads(response)
        assert payload["id"] == 1
        assert payload["result"] == "ok"


def test_lsp_websocket_invalid_json(client):
    lsp_controller.service = FakeService()
    with client.websocket_connect("/ws/lsp") as websocket:
        websocket.send_text("not-json")
        response = websocket.receive_text()
        payload = json.loads(response)
        assert payload["message"] == "invalid_json"
