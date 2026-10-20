"""Meaningful HTTP and content checks: python -m unittest discover -s tests -v."""
import copy
from html.parser import HTMLParser
import json
import os
import re
import unittest
from unittest.mock import patch
from urllib.parse import urlsplit
from xml.etree import ElementTree

from fastapi.testclient import TestClient

from app.content import load_content, page_context, public_origin, validate_asset, validate_content
from app.main import app


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.assets = set()
        self.links = []
        self.ids = []
        self.h1_count = 0

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "h1":
            self.h1_count += 1
        if "id" in attributes:
            self.ids.append(attributes["id"])
        for key in ("src", "href"):
            value = attributes.get(key, "")
            if value.startswith("/static/") or value == "/theme.css":
                self.assets.add(value)
        if tag == "a":
            self.links.append(attributes.get("href", ""))


class SiteTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {"SITE_URL": ""})
        self.environment.start()
        self.addCleanup(self.environment.stop)
        self.client = TestClient(app)
        self.content = load_content()

    def parse(self, response):
        parser = PageParser()
        parser.feed(response.text)
        return parser

    def test_home_content_and_real_contact_actions(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        for text in ("БАГМУТ", "Руслан Павлик", "Казачья", "Джигитовка", "8А"):
            # The page uses lower-case джигитовка in several text blocks.
            self.assertIn(text.casefold(), response.text.casefold())
        self.assertNotIn("БАЛФЕСТ", response.text)
        self.assertNotIn("{{", response.text)
        self.assertIn("tel:+79500042703", response.text)
        self.assertIn("mailto:bagmut.spb@mail.ru", response.text)
        self.assertIn("https://vk.com/public_bagmut_dzhigitovka", response.text)
        parser = self.parse(response)
        self.assertEqual(parser.h1_count, 1)
        self.assertEqual(len(parser.ids), len(set(parser.ids)))

    def test_local_assets_exist_on_all_pages(self):
        paths = ["/", "/sources", "/programs/theatre", "/does-not-exist"]
        assets = set()
        for path in paths:
            assets.update(self.parse(self.client.get(path)).assets)
        self.assertGreaterEqual(len(assets), 5)
        for asset in assets:
            response = self.client.get(asset)
            self.assertEqual(response.status_code, 200, asset)
        self.assertIn("--bg:#F4F0E6", self.client.get("/theme.css").text)

    def test_navigation_targets_and_every_direction(self):
        response = self.client.get("/")
        parser = self.parse(response)
        ids = set(parser.ids)
        for link in parser.links:
            url = urlsplit(link)
            if not url.scheme and url.path in ("", "/") and url.fragment:
                self.assertIn(url.fragment, ids, link)
        for program in self.content["programs"]:
            response = self.client.get("/programs/" + program["id"])
            self.assertEqual(response.status_code, 200, program["id"])
            self.assertEqual(self.parse(response).h1_count, 1)
            self.assertIn(program["intro"], response.text)
            for source_id in program["sourceIds"]:
                source = next(item for item in self.content["sources"] if item["id"] == source_id)
                self.assertIn(source["url"].replace("&", "&amp;"), response.text)

    def test_sources_page_and_internal_source_anchors(self):
        response = self.client.get("/sources")
        self.assertEqual(response.status_code, 200)
        ids = self.parse(response).ids
        for source in self.content["sources"]:
            self.assertIn(source["id"], ids)
            self.assertIn(source["name"], response.text)

    def test_unknown_pages_and_missing_static_are_branded_404s(self):
        for path in ("/missing", "/programs/unknown", "/static/missing.png"):
            response = self.client.get(path)
            self.assertEqual(response.status_code, 404, path)
            self.assertIn("На главную", response.text)
            self.assertIn("noindex,nofollow", response.text)

    def test_unconfigured_domain_does_not_publish_fake_urls(self):
        response = self.client.get("/")
        self.assertIn("noindex,nofollow", response.text)
        self.assertNotIn('rel="canonical"', response.text)
        self.assertIn("Disallow: /", self.client.get("/robots.txt").text)
        root = ElementTree.fromstring(self.client.get("/sitemap.xml").text)
        self.assertEqual(len(root), 0)

    def test_configured_metadata_and_sitemap(self):
        with patch.dict(os.environ, {"SITE_URL": "https://bagmut.example"}):
            response = self.client.get("/")
            self.assertIn('rel="canonical" href="https://bagmut.example/"', response.text)
            self.assertIn("index,follow,max-image-preview:large", response.text)
            self.assertIn("https://bagmut.example/sitemap.xml", self.client.get("/robots.txt").text)
            root = ElementTree.fromstring(self.client.get("/sitemap.xml").text)
            locations = [item.text for item in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc")]
            self.assertEqual(len(locations), len(self.content["programs"]) + 2)
            for location in locations:
                self.assertEqual(self.client.get(urlsplit(location).path).status_code, 200)
            self.assertIn("https://bagmut.example/programs/archery",
                          self.client.get("/programs/archery").text)

    def test_organization_schema_is_valid_json_not_festival_event(self):
        response = self.client.get("/")
        match = re.search(r'<script type="application/ld\+json" id="organization-schema">(.*?)</script>',
                          response.text, re.S)
        self.assertIsNotNone(match)
        schema = json.loads(match.group(1))
        self.assertEqual(schema["@type"], "Organization")
        self.assertEqual(schema["telephone"], "+79500042703")
        self.assertNotIn("startDate", schema)

    def test_request_host_cannot_set_canonical(self):
        response = self.client.get("/", headers={"Host": "untrusted.example"})
        self.assertNotIn("untrusted.example", response.text)
        self.assertNotIn('rel="canonical"', response.text)

    def test_html_and_json_are_escaped(self):
        content = copy.deepcopy(self.content)
        content["hero"]["description"] = '<script>alert("test")</script>'
        content["site"]["description"] = "</script><script>alert(1)</script>"
        with patch("app.main.load_content", return_value=content):
            response = self.client.get("/")
        self.assertNotIn('<script>alert', response.text)
        self.assertIn("&lt;script&gt;", response.text)
        self.assertIn(r"\u003c/script\u003e", response.text)

    def test_invalid_content_is_rejected(self):
        content = copy.deepcopy(self.content)
        content["contacts"]["vkUrl"] = "javascript:alert(1)"
        with self.assertRaises(ValueError):
            validate_content(content)
        content = copy.deepcopy(self.content)
        content["theme"]["accent"] = "red;display:none"
        with self.assertRaises(ValueError):
            validate_content(content)
        content = copy.deepcopy(self.content)
        content["programs"][0]["sourceIds"] = ["unknown"]
        with self.assertRaises(ValueError):
            validate_content(content)
        with self.assertRaises(ValueError):
            validate_asset("../main.py")
        for origin in ("http://bagmut.example", "https://bagmut.example/path",
                       "https://user:pass@bagmut.example"):
            with patch.dict(os.environ, {"SITE_URL": origin}):
                with self.assertRaises(ValueError):
                    public_origin(self.content)

    def test_health_and_response_headers(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"status": "ok"})
        self.assertEqual(response.headers["X-Content-Type-Options"], "nosniff")
        self.assertEqual(self.client.get("/").headers["X-Frame-Options"], "DENY")


if __name__ == "__main__":
    unittest.main()
