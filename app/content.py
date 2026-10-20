"""Editable content and validated template context, adapted from BALFEST."""
from datetime import date
import json
import os
from pathlib import Path
import re
from urllib.parse import quote, urlsplit

BASE_DIR = Path(__file__).resolve().parent
CONTENT_FILE = BASE_DIR / "data" / "content.json"


def validate_https(value: str) -> None:
    parsed = urlsplit(value)
    if (parsed.scheme != "https" or not parsed.netloc or not parsed.hostname
            or parsed.username or parsed.password
            or any(char.isspace() or char in '<>"\\' for char in value)):
        raise ValueError("Expected a valid HTTPS URL")


def validate_asset(relative_path: str) -> None:
    static = (BASE_DIR / "static").resolve()
    target = (static / relative_path).resolve()
    if not target.is_relative_to(static) or not target.is_file():
        raise ValueError(f"Missing or invalid static asset: {relative_path}")


def validate_content(content: dict) -> None:
    def walk(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if key.lower().endswith("url") and item:
                    validate_https(item)
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(content)
    for color in content["theme"].values():
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError("Theme colors must use #RRGGBB")
    contacts = content["contacts"]
    if not re.fullmatch(r"[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+", contacts["email"]):
        raise ValueError("Invalid contact email")
    if not contacts["phones"]:
        raise ValueError("At least one contact phone is required")
    for phone in contacts["phones"]:
        if not re.fullmatch(r"\+7\d{10}", phone["value"]):
            raise ValueError("Phone numbers must use +7XXXXXXXXXX")
    source_ids = [source["id"] for source in content["sources"]]
    program_ids = [program["id"] for program in content["programs"]]
    if len(source_ids) != len(set(source_ids)) or len(program_ids) != len(set(program_ids)):
        raise ValueError("Duplicate content IDs")
    categories = {item["id"] for item in content["categories"]}
    for program in content["programs"]:
        if not re.fullmatch(r"[a-z][a-z0-9-]*", program["id"]):
            raise ValueError("Invalid program slug")
        if program["category"] not in categories:
            raise ValueError("Unknown program category")

    def check_sources(value):
        if isinstance(value, dict):
            refs = value.get("sourceIds", [])
            if "sourceId" in value:
                refs = [*refs, value["sourceId"]]
            if not set(refs).issubset(source_ids):
                raise ValueError("Unknown source reference")
            for item in value.values():
                check_sources(item)
        elif isinstance(value, list):
            for item in value:
                check_sources(item)

    check_sources(content)
    date.fromisoformat(content["site"]["checkedAt"])
    for asset in ("assets/horse.svg", "assets/favicon.svg", "assets/og-image.svg"):
        validate_asset(asset)


def load_content() -> dict:
    """Read per request so an editor can update JSON without rebuilding."""
    content = json.loads(CONTENT_FILE.read_text(encoding="utf-8"))
    validate_content(content)
    return content


def public_origin(content: dict) -> str:
    """Use configured origin only; never trust a request Host for canonical URLs."""
    value = os.environ.get("SITE_URL", content["site"].get("url", "")).strip().rstrip("/")
    if not value:
        return ""
    validate_https(value)
    parsed = urlsplit(value)
    if parsed.path or parsed.query or parsed.fragment:
        raise ValueError("SITE_URL must be an HTTPS origin, without a path or query")
    return value


def page_context(content: dict, *, page_path: str = "/", title: str | None = None,
                 description: str | None = None) -> dict:
    origin = public_origin(content)
    contacts = content["contacts"]
    schema = {
        "@context": "https://schema.org",
        "@type": "Organization",
        "name": content["site"]["fullName"],
        "alternateName": "БАГМУТ",
        "description": content["site"]["description"],
        "telephone": contacts["phones"][0]["value"],
        "email": contacts["email"],
        "sameAs": [contacts["vkUrl"]],
        "address": {
            "@type": "PostalAddress",
            "addressLocality": contacts["locality"],
            "addressRegion": "Ленинградская область",
            "streetAddress": "2-я Красная дорога, 8А",
            "addressCountry": "RU",
        },
    }
    if origin:
        schema["url"] = origin + "/"
    source_index = {item["id"]: item for item in content["sources"]}
    return {
        "c": content, "title": title or content["site"]["title"],
        "description": description or content["site"]["description"],
        "canonical": origin + page_path if origin else "",
        "og_image": origin + "/static/assets/og-image.svg" if origin else "",
        "indexable": bool(origin), "organization_schema": schema,
        "source_index": source_index, "year": date.today().year,
        "checked_label": date.fromisoformat(content["site"]["checkedAt"]).strftime("%d.%m.%Y"),
        "lesson_mailto": "mailto:" + contacts["email"] + "?subject=" + quote("Занятия в центре БАГМУТ"),
        "event_mailto": "mailto:" + contacts["email"] + "?subject=" + quote(content["events"]["subject"])
            + "&body=" + quote("Здравствуйте!\nДата: \nМесто: \nФормат события: \nАудитория: \nПлощадка: \nБюджет: \nКонтакт для связи: \n"),
    }
