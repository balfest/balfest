"""Load the editable site content and prepare data for Jinja templates."""
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import re
from urllib.parse import urlsplit

BASE_DIR = Path(__file__).resolve().parent
CONTENT_FILE = BASE_DIR / "data" / "content.json"
MOSCOW = timezone(timedelta(hours=3))
MONTHS = ("января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря")
WEEKDAYS = ("Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье")


def load_content() -> dict:
    """Read on each request so content edits do not require a build."""
    content = json.loads(CONTENT_FILE.read_text(encoding="utf-8"))

    def validate(value):
        if isinstance(value, dict):
            for key, item in value.items():
                if (key.lower().endswith("url") or key == "vk") and item:
                    parsed = urlsplit(item)
                    if parsed.scheme != "https" or not parsed.netloc or any(c in item for c in '\r\n<>"'):
                        raise ValueError(f"Expected an HTTPS link: {key}")
                if key == "logo" and item:
                    validate_asset(item)
                validate(item)
        elif isinstance(value, list):
            for item in value:
                validate(item)

    validate(content)
    for color in content["theme"].values():
        if not re.fullmatch(r"#[0-9a-fA-F]{6}", color):
            raise ValueError("Theme colors must use #RRGGBB")
    validate_asset("assets/" + content["openCall"]["image"])
    if content["tickets"]["status"] == "on_sale" and not content["tickets"]["url"]:
        raise ValueError("Ticket sales require a ticket URL")
    if content["venue"]["confirmed"] and not all(content["venue"][key] for key in ("name", "address")):
        raise ValueError("A confirmed venue requires a name and address")
    if content["contacts"]["emailVerified"] and not re.fullmatch(r"[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+", content["contacts"]["email"]):
        raise ValueError("Invalid contact email")
    return content


def validate_asset(relative_path: str) -> None:
    static = (BASE_DIR / "static").resolve()
    target = (static / relative_path).resolve()
    if not target.is_relative_to(static) or not target.is_file():
        raise ValueError(f"Missing or invalid static asset: {relative_path}")


def long_date(value: date) -> str:
    return f"{value.day} {MONTHS[value.month - 1]} {value.year}"


def page_context(content: dict, *, today: date | None = None) -> dict:
    site = content["site"]
    start, end = (date.fromisoformat(site[key]) for key in ("startDate", "endDate"))
    if end < start:
        raise ValueError("Festival end precedes its start")
    date_label = (f"{start.day}–{end.day} {MONTHS[start.month - 1]} {start.year}"
                  if (start.year, start.month) == (end.year, end.month)
                  else f"{long_date(start)} — {long_date(end)}")
    call = content["openCall"]
    deadline = date.fromisoformat(call["deadline"]) if call.get("deadlineConfirmed") and call.get("deadline") else None
    call_visible = bool(call["enabled"]) and (deadline is None or (today or datetime.now(MOSCOW).date()) <= deadline)
    on_sale = content["tickets"]["status"] == "on_sale" and bool(content["tickets"]["url"])
    options = [item for item in content["tickets"]["options"] if item.get("confirmed")]
    for item in options:
        if not isinstance(item["price"], (int, float)) or item["price"] < 0:
            raise ValueError("Ticket price must be nonnegative")
    days = []
    seen_dates = set()
    direction_ids = [item["id"] for item in content["directions"]]
    if len(set(direction_ids)) != len(direction_ids):
        raise ValueError("Duplicate dance direction IDs")
    for item in content["program"]["days"]:
        day = date.fromisoformat(item["date"])
        if not start <= day <= end or day in seen_dates:
            raise ValueError("Invalid or duplicate program date")
        seen_dates.add(day)
        sessions = [session for session in item["sessions"] if session.get("confirmed")]
        for session in sessions:
            if session["directionId"] not in direction_ids or not re.fullmatch(r"([01]\d|2[0-3]):[0-5]\d", session["time"]):
                raise ValueError("Invalid program session direction or time")
        days.append(dict(date=day.isoformat(), weekday=WEEKDAYS[day.weekday()], month=MONTHS[day.month - 1], year=day.year, number=day.day, sessions=sessions))
    canonical = site["url"].rstrip("/") + "/"
    og_image = canonical + "static/assets/og-image.jpg"
    schema = {
        "@context": "https://schema.org", "@type": "Event", "name": site["name"],
        "alternateName": site["latinName"], "description": site["description"], "url": canonical,
        "startDate": site["startDate"], "endDate": site["endDate"], "inLanguage": "ru",
        "eventAttendanceMode": "https://schema.org/OfflineEventAttendanceMode",
        "eventStatus": "https://schema.org/EventScheduled", "image": [og_image],
        "location": {"@type": "City", "name": site["city"], "address": {"@type": "PostalAddress", "addressLocality": site["city"], "addressCountry": "RU"}},
        "organizer": {"@type": "Organization", "name": "БАЛФЕСТ", "url": canonical, "sameAs": [content["contacts"]["vk"]]},
    }
    venue = content["venue"]
    if venue["confirmed"]:
        schema["location"] = {"@type": "Place", "name": venue["name"], "address": {"@type": "PostalAddress", "streetAddress": venue["address"], "addressLocality": site["city"], "addressCountry": "RU"}}
    if on_sale and options:
        schema["offers"] = [{"@type": "Offer", "name": item["name"], "url": content["tickets"]["url"], "price": item["price"], "priceCurrency": "RUB"} for item in options]
    return dict(
        c=content, date_label=date_label, days=days, deadline=deadline,
        deadline_label=long_date(deadline) if deadline else "", call_visible=call_visible,
        on_sale=on_sale, ticket_options=options,
        ticket_status="Билеты в продаже" if on_sale else "Билеты скоро в продаже",
        program_status="Программа опубликована" if content["program"]["status"] == "published" else "Программа формируется",
        venue_status=venue["name"] if venue["confirmed"] else "Площадка будет объявлена",
        studios=[item for item in content["studios"] if item.get("confirmed")],
        partners=[item for item in content["partners"] if item.get("confirmed")],
        canonical=canonical, og_image=og_image, event_schema=schema,
    )
