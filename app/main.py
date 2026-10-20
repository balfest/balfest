"""Run from the project root: python -m uvicorn app.main:app --reload."""
from html import escape

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException

from .content import BASE_DIR, load_content, page_context, public_origin

app = FastAPI(title="БАГМУТ — центр казачьей джигитовки",
              docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.middleware("http")
async def response_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    response.headers["X-Frame-Options"] = "DENY"
    return response


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(
        request=request, name="index.html", context=page_context(load_content()))


@app.get("/programs/{slug}", response_class=HTMLResponse)
def program(request: Request, slug: str):
    content = load_content()
    item = next((item for item in content["programs"] if item["id"] == slug), None)
    if item is None:
        raise HTTPException(status_code=404)
    title = item["title"].replace("\n", " ")
    context = page_context(content, page_path=f"/programs/{slug}",
                           title=f"{title} — БАГМУТ", description=item["short"])
    context["program"] = item
    return templates.TemplateResponse(request=request, name="program.html", context=context)


@app.get("/sources", response_class=HTMLResponse)
def sources(request: Request):
    context = page_context(load_content(), page_path="/sources",
                           title="Материалы о центре — БАГМУТ")
    return templates.TemplateResponse(request=request, name="sources.html", context=context)


@app.get("/healthz")
def health():
    return {"status": "ok"}


@app.get("/theme.css")
def theme():
    colors = load_content()["theme"]
    names = {"bg": "background", "surface": "surface", "accent": "accent",
             "text": "text", "muted": "muted"}
    css = ":root{" + "".join(f"--{name}:{colors[key]};" for name, key in names.items()) + "}\n"
    return Response(css, media_type="text/css", headers={"Cache-Control": "no-cache"})


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    origin = public_origin(load_content())
    if not origin:
        return "User-agent: *\nDisallow: /\n"
    return f"User-agent: *\nAllow: /\nDisallow: /healthz\n\nSitemap: {origin}/sitemap.xml\n"


@app.get("/sitemap.xml")
def sitemap():
    content = load_content()
    origin = public_origin(content)
    paths = ["/", *[f"/programs/{item['id']}" for item in content["programs"]], "/sources"]
    entries = "".join(f"<url><loc>{escape(origin + path)}</loc></url>" for path in paths) if origin else ""
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           + entries + "</urlset>\n")
    return Response(xml, media_type="application/xml")


@app.exception_handler(HTTPException)
def http_error(request: Request, exc: HTTPException):
    if exc.status_code == 404:
        context = page_context(load_content(), title="Страница не найдена — БАГМУТ")
        context["indexable"] = False
        context["canonical"] = ""
        return templates.TemplateResponse(
            request=request, name="404.html", context=context, status_code=404)
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code, headers=exc.headers)
