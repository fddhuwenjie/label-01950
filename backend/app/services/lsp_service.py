import asyncio
import json
import logging
from asyncio.subprocess import Process
from typing import Awaitable, Callable, Optional

from app.core.config import settings
from app.core.exceptions import AppError

logger = logging.getLogger("lsp-service")


class LspSession:
    def __init__(self, process: Process) -> None:
        self.process = process
        self._stdout_task: Optional[asyncio.Task[None]] = None
        self._stderr_task: Optional[asyncio.Task[None]] = None

    async def start(self, on_message: Callable[[dict], Awaitable[None]]) -> None:
        self._stdout_task = asyncio.create_task(self._read_stdout(on_message))
        self._stderr_task = asyncio.create_task(self._read_stderr())

    async def _read_stdout(self, on_message: Callable[[dict], Awaitable[None]]) -> None:
        buffer = b""
        stdout = self.process.stdout
        if stdout is None:
            return
        while True:
            chunk = await stdout.read(4096)
            if not chunk:
                break
            buffer += chunk
            while True:
                header_end = buffer.find(b"\r\n\r\n")
                if header_end == -1:
                    break
                header = buffer[:header_end].decode("utf-8", errors="ignore")
                content_length = 0
                for line in header.split("\r\n"):
                    if line.lower().startswith("content-length:"):
                        content_length = int(line.split(":", 1)[1].strip())
                if content_length == 0:
                    buffer = buffer[header_end + 4 :]
                    continue
                start = header_end + 4
                end = start + content_length
                if len(buffer) < end:
                    break
                body = buffer[start:end]
                buffer = buffer[end:]
                try:
                    payload = json.loads(body.decode("utf-8"))
                    await on_message(payload)
                except json.JSONDecodeError:
                    logger.warning("invalid_json_from_lsp")

    async def _read_stderr(self) -> None:
        stderr = self.process.stderr
        if stderr is None:
            return
        while True:
            line = await stderr.readline()
            if not line:
                break
            logger.warning("lsp_stderr %s", line.decode("utf-8", errors="ignore").strip())

    async def send(self, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        header = f"Content-Length: {len(body)}\r\n\r\n".encode("utf-8")
        stdin = self.process.stdin
        if stdin is None:
            raise AppError("lsp_stdin_unavailable", status_code=500)
        stdin.write(header + body)
        await stdin.drain()

    async def stop(self) -> None:
        if self.process.returncode is None:
            self.process.terminate()
            try:
                await asyncio.wait_for(self.process.wait(), timeout=3)
            except asyncio.TimeoutError:
                self.process.kill()
        if self._stdout_task:
            self._stdout_task.cancel()
        if self._stderr_task:
            self._stderr_task.cancel()


class LspService:
    def __init__(self) -> None:
        self._semaphore = asyncio.Semaphore(settings.lsp_max_concurrent_sessions)

    async def create_session(self) -> LspSession:
        await self._semaphore.acquire()
        try:
            process = await asyncio.create_subprocess_exec(
                settings.lsp_command,
                *settings.lsp_args.split(),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            return LspSession(process)
        except FileNotFoundError as exc:
            self._semaphore.release()
            raise AppError("sqlfluff_not_found", status_code=500) from exc

    def release(self) -> None:
        self._semaphore.release()
