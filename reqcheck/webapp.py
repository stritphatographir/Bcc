import asyncio
import json
import logging
import re
from pathlib import Path, PureWindowsPath
from tempfile import TemporaryDirectory
from typing import Annotated

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, TypeAdapter, ValidationError

from .clarifier import Answer
from .config import Settings
from .loader import load
from .pipeline import analyze
from .report import render_html, render_markdown

app = FastAPI(title="Проверка требований")
assets = Path(__file__).with_name("web")
app.mount("/assets", StaticFiles(directory=assets, check_dir=False), name="assets")
logger = logging.getLogger(__name__)
MAX_BYTES = 8 * 1024 * 1024
EXTENSIONS = {".md", ".txt", ".pdf", ".docx", ".html", ".htm"}


class AnswerInput(BaseModel):
    id: str = Field(max_length=30)
    question: str = Field(max_length=5000)
    text: str = Field(min_length=1, max_length=2000)


class StaleQuestions(ValueError):
    pass


@app.get("/")
def index():
    return FileResponse(assets / "index.html")


@app.post("/api/analyze")
async def upload(document: Annotated[UploadFile, File()],
                 answers: Annotated[str, Form(max_length=64_000)] = "[]"):
    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", PureWindowsPath(document.filename or "").name)
    try:
        try:
            submitted = TypeAdapter(list[AnswerInput]).validate_json(answers)
        except ValidationError:
            raise HTTPException(422, "Формат ответов изменился. Откройте вопросы из нового отчёта.") from None
        if Path(name).suffix.lower() not in EXTENSIONS:
            raise HTTPException(415, "Выберите PDF, DOCX, Markdown, TXT или HTML.")
        content = await document.read(MAX_BYTES + 1)
    finally:
        await document.close()
    if not content:
        raise HTTPException(422, "Файл пуст.")
    if len(content) > MAX_BYTES:
        raise HTTPException(413, "Размер файла превышает 8 МБ.")

    async def stream():
        events = asyncio.Queue()
        loop = asyncio.get_running_loop()

        def progress(stage):
            loop.call_soon_threadsafe(events.put_nowait, {"type": "stage", "text": stage})

        def collect(items):
            known = {(item.id, item.text): item for item in items}
            updated = []
            for answer in submitted:
                item = known.get((answer.id, answer.question))
                if item is None:
                    raise StaleQuestions
                updated.append(Answer(question=item, text=answer.text.strip()))
            return [answer for answer in updated if answer.text]

        def run():
            with TemporaryDirectory(prefix="reqcheck-") as temporary:
                path = Path(temporary) / name
                path.write_bytes(content)
                result = analyze(path, Settings.from_env(), progress=progress, collect=collect)
                markdown = render_markdown(result)
                return {
                    "type": "result", "analysis": result.model_dump(mode="json"),
                    "markdown": markdown, "html": render_html(markdown, result.quality),
                    "source": [source.model_dump() for source in load(path)],
                }

        async def publish():
            try:
                payload = await asyncio.to_thread(run)
            except StaleQuestions:
                payload = {"type": "error", "text": "Вопросы изменились. Запустите проверку файла и ответьте снова."}
            except Exception:
                logger.exception("Document analysis failed")
                payload = {"type": "error", "text": "Проверка прервалась. Проверьте формат файла и настройки модели."}
            await events.put(payload)

        worker = asyncio.create_task(publish())
        try:
            while True:
                try:
                    event = await asyncio.wait_for(events.get(), timeout=15)
                except TimeoutError:
                    yield ": keepalive\n\n"
                    continue
                yield "data: " + json.dumps(event, ensure_ascii=False) + "\n\n"
                if event["type"] != "stage":
                    break
        finally:
            worker.cancel()

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-store"})
