"""Run: python -m unittest discover -s tests -v."""
import copy
from datetime import date
from html.parser import HTMLParser
import json
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit

from fastapi.testclient import TestClient

from app.content import load_content, page_context
from app.main import app


class AssetParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = set()

    def handle_starttag(self, tag, attrs):
        for name, value in attrs:
            if name in ("src", "href") and value and "/static/" in value:
                self.assets.add(urlsplit(value).path)
            if name in ("srcset", "imagesrcset") and value:
                self.assets.update(urlsplit(item.strip().split()[0]).path for item in value.split(","))


class SiteTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def test_home_and_assets(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        for text in ("БАЛФЕСТ", "Создаём БАЛФЕСТ", "Спортивные", "4–6 декабря 2026"):
            self.assertIn(text, response.text)
        self.assertNotIn("{{", response.text)
        parser = AssetParser()
        parser.feed(response.text)
        self.assertGreater(len(parser.assets), 8)
        for asset in parser.assets:
            self.assertEqual(self.client.get(asset).status_code, 200, asset)
        self.assertIn("--bg:#0b1422", self.client.get("/theme.css").text)

    def test_metadata_and_not_found(self):
        self.assertEqual(self.client.get("/sitemap.xml").status_code, 200)
        self.assertIn("Sitemap:", self.client.get("/robots.txt").text)
        for path in ("/missing", "/static/missing.png"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404)
            self.assertIn("На главную", response.text)

    def test_deadline_is_evaluated_per_request(self):
        c = copy.deepcopy(load_content())
        c["openCall"].update(enabled=True, deadline="2026-11-01", deadlineConfirmed=True)
        self.assertTrue(page_context(c, today=date(2026, 11, 1))["call_visible"])
        self.assertFalse(page_context(c, today=date(2026, 11, 2))["call_visible"])
        c["openCall"]["deadline"] = "2000-01-01"
        with patch("app.main.load_content", return_value=c):
            self.assertNotIn('id="participation"', self.client.get("/").text)

    def test_confirmed_sales_and_venue(self):
        c = copy.deepcopy(load_content())
        c["tickets"].update(status="on_sale", url="https://example.com/tickets", options=[dict(confirmed=True, name="День", price=1000), dict(confirmed=False, name="Черновик", price=2000)])
        c["venue"].update(confirmed=True, name="Зал", address="Адрес")
        with patch("app.main.load_content", return_value=c):
            text = self.client.get("/").text
        self.assertIn("Билеты в продаже", text)
        self.assertIn("1000 ₽", text)
        self.assertNotIn("Черновик", text)
        self.assertIn("Адрес", text)
        schema = page_context(c)["event_schema"]
        self.assertEqual(schema["location"]["@type"], "Place")
        self.assertEqual(len(schema["offers"]), 1)

    def test_content_is_escaped(self):
        c = copy.deepcopy(load_content())
        c["hero"]["description"] = '<script>alert("test")</script>'
        c["site"]["description"] = "</script><script>alert(1)</script>"
        with patch("app.main.load_content", return_value=c):
            response = self.client.get("/")
        self.assertNotIn('<script>alert', response.text)
        self.assertIn("&lt;script&gt;", response.text)
        self.assertIn("\\u003c/script\\u003e", response.text)


if __name__ == "__main__":
    unittest.main()
