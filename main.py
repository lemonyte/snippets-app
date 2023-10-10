from __future__ import annotations

from uuid import UUID  # noqa: TCH003

from deta import Drive
from fastapi import FastAPI, HTTPException, Request, UploadFile, status
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from database import DetaDB, SnippetExistsError, SnippetNotFoundError
from models import Snippet

app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")
db = DetaDB("snippets")
pending_db = DetaDB("pending_snippets")
images = Drive("images")


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Response:
    snippets = db.fetch()
    return templates.TemplateResponse("index.html", {"request": request, "snippets": snippets})


@app.get("/create", response_class=HTMLResponse)
async def create(request: Request) -> Response:
    return templates.TemplateResponse("create.html", {"request": request})


@app.get("/snippet/{id}", response_class=HTMLResponse)
async def view_snippet(id: UUID, request: Request) -> Response:
    snippet = await api_snippet_get(id)
    return templates.TemplateResponse("snippet.html", {"request": request, "snippet": snippet})


@app.get("/raw/{id}", response_class=PlainTextResponse)
async def raw(id: UUID) -> str:
    snippet = await api_snippet_get(id)
    return snippet.content


@app.post("/api/snippet", response_model=Snippet)
async def api_snippet_post(snippet: Snippet) -> Snippet:
    try:
        pending_db.put(snippet)
    except SnippetExistsError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT) from exc
    return snippet


@app.get("/api/snippet/{id}", response_model=Snippet)
async def api_snippet_get(id: UUID) -> Snippet:
    try:
        snippet = db.get(id)
    except SnippetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc
    return snippet


@app.get("/api/image/{id}")
async def api_image_get(id: UUID) -> Response:
    filename = f"{id}.png"
    if filename not in images.list().get(  # pyright: ignore[reportOptionalMemberAccess, reportGeneralTypeIssues]
        "names",
        {},
    ):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    image = images.get(filename).read()  # pyright: ignore[reportOptionalMemberAccess]
    headers = {
        "Cache-Control": "public, max-age=604800, immutable",
    }
    return Response(image, headers=headers, media_type="image/png")


@app.post("/api/image/{id}")
async def api_image_post(id: UUID, image: UploadFile) -> None:
    filename = f"{id}.png"
    if filename in images.list().get(  # pyright: ignore[reportOptionalMemberAccess, reportGeneralTypeIssues]
        "names",
        {},
    ):
        raise HTTPException(status_code=status.HTTP_409_CONFLICT)
    images.put(filename, await image.read())


@app.get("/api/verify/{id}")
async def api_verify(id: UUID) -> None:
    try:
        snippet = pending_db.get(id)
        db.put(snippet)
        pending_db.delete(id)
    except SnippetNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND) from exc


@app.exception_handler(status.HTTP_404_NOT_FOUND)
async def not_found_handler(request: Request, exception: HTTPException) -> Response:
    if request.url.path.startswith("/api"):
        return await http_exception_handler(request, exception)
    return templates.TemplateResponse("404.html", {"request": request}, status.HTTP_404_NOT_FOUND)
