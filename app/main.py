"""Run from the project root: python -m uvicorn app.main:app --reload."""
from html import escape

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException

from .content import BASE_DIR, load_content, page_context

app = FastAPI(title="БАЛФЕСТ IV", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


@app.get("/", response_class=HTMLResponse)
def index(request: Request):
    return templates.TemplateResponse(request=request, name="index.html", context=page_context(load_content()))


@app.get("/theme.css")
def theme():
    colors = load_content()["theme"]
    names = {"bg": "background", "surface": "surface", "gold": "gold", "text": "text", "muted": "muted"}
    css = ":root{" + "".join(f"--{name}:{colors[key]};" for name, key in names.items()) + "}\n"
    return Response(css, media_type="text/css", headers={"Cache-Control": "no-cache"})


@app.get("/robots.txt", response_class=PlainTextResponse)
def robots():
    canonical = load_content()["site"]["url"].rstrip("/")
    return f"User-agent: *\nAllow: /\n\nSitemap: {canonical}/sitemap.xml\n"


@app.get("/sitemap.xml")
def sitemap():
    canonical = escape(load_content()["site"]["url"].rstrip("/") + "/")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
           f'<url><loc>{canonical}</loc></url></urlset>\n')
    return Response(xml, media_type="application/xml")


@app.exception_handler(HTTPException)
def http_error(request: Request, exc: HTTPException):
    if exc.status_code == 404:
        return templates.TemplateResponse(request=request, name="404.html", status_code=404)
    return PlainTextResponse(str(exc.detail), status_code=exc.status_code, headers=exc.headers)
