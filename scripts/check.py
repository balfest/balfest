#!/usr/bin/env python3
"""Validate output and editorial safeguards, without third-party dependencies."""
from __future__ import annotations
import copy
import json
import re
import tempfile
import unittest
from collections import Counter
from datetime import date
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit
from xml.etree import ElementTree
from build import ROOT, build

class Page(HTMLParser):
    def __init__(self, text):
        super().__init__(); self.tags=[]; self.ids=[]; self.links=[]; self.resources=[]; self.schema=''; self.capture=False; self.feed(text)
    def handle_starttag(self,tag,attrs):
        a=dict(attrs); self.tags.append((tag,a))
        if 'id' in a:self.ids.append(a['id'])
        if tag=='a':self.links.append(a)
        if tag in ['img','script'] and a.get('src'):self.resources.append(a['src'])
        if tag=='link' and a.get('rel') in ['stylesheet','icon','apple-touch-icon']:self.resources.append(a['href'])
        if tag=='script' and a.get('id')=='event-schema':self.capture=True
    def handle_endtag(self,tag):
        if tag=='script':self.capture=False
    def handle_data(self,data):
        if self.capture:self.schema+=data

class SiteChecks(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.content=json.loads((ROOT/'source/content.json').read_text())
        cls.page_text=(ROOT/'dist/index.html').read_text()
        cls.page=Page(cls.page_text)
    def test_semantics_and_navigation(self):
        p=self.page
        self.assertEqual(sum(tag=='h1' for tag,a in p.tags),1)
        self.assertTrue(any(tag=='html' and a.get('lang')=='ru' for tag,a in p.tags))
        self.assertFalse([i for i,count in Counter(p.ids).items() if count>1])
        for link in p.links:
            self.assertTrue(link.get('href'))
            if link['href'].startswith('#'):self.assertIn(link['href'][1:],p.ids)
            if link.get('target')=='_blank':self.assertIn('noopener',link.get('rel',''))
        self.assertIn('mobile-menu',p.ids)
    def test_resources_and_images(self):
        for resource in self.page.resources:
            self.assertTrue((ROOT/'dist'/urlsplit(resource).path).is_file(),resource)
        for tag,a in self.page.tags:
            if tag=='img':
                self.assertIn('alt',a);self.assertGreater(int(a['width']),0);self.assertGreater(int(a['height']),0)
                for item in a.get('srcset','').split(','):
                    if item.strip():self.assertTrue((ROOT/'dist'/item.strip().split()[0]).is_file())
        self.assertLess((ROOT/'dist/assets/hero-768.webp').stat().st_size,100000)
        self.assertLess((ROOT/'dist/assets/hero-2048.webp').stat().st_size,400000)
    def test_seo(self):
        tags=self.page.tags
        self.assertTrue(any(t=='link' and a.get('rel')=='canonical' and a['href']=='https://balfest.ru/' for t,a in tags))
        schema=json.loads(self.page.schema)
        self.assertEqual(schema['@type'],'Event');self.assertEqual(schema['startDate'],'2026-12-04');self.assertEqual(schema['endDate'],'2026-12-06')
        self.assertNotIn('offers',schema);self.assertNotIn('performer',schema)
        self.assertEqual(schema['location']['name'],'Санкт-Петербург')
        self.assertEqual(schema['organizer']['sameAs'],['https://vk.com/balfest'])
        self.assertIn('Sitemap: https://balfest.ru/sitemap.xml',(ROOT/'dist/robots.txt').read_text())
        xml=ElementTree.parse(ROOT/'dist/sitemap.xml')
        self.assertEqual(xml.find('.//{*}loc').text,'https://balfest.ru/')
        self.assertIn('noindex',(ROOT/'dist/404.html').read_text())
    def test_editorial_guards(self):
        p=self.page_text
        self.assertNotIn('mailto:',p);self.assertNotIn('hello@balfest.ru',p)
        for fragment in ['начале ноября','до 15 октября','До 15 ноября','club227666778','ivansko@','₽','Основной день']:
            self.assertNotIn(fragment,p)
        self.assertEqual(p.count('class="direction-card"'),8)
        self.assertNotIn('analytics-config',p)
        self.assertNotIn('{{',p)
    def variant(self,mutate,today=date(2026,10,12)):
        content=copy.deepcopy(self.content);mutate(content)
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp);path=root/'test-content.json';path.write_text(json.dumps(content,ensure_ascii=False))
            build(path,root/'out',today)
            return (root/'out/index.html').read_text()
    def test_disable_open_call(self):
        text=self.variant(lambda c:c['openCall'].update(enabled=False))
        self.assertNotIn('id="participation"',text);self.assertNotIn('href="#participation"',text)
    def test_deadline_expiry(self):
        mutate=lambda c:c['openCall'].update(deadline='2026-10-15',deadlineConfirmed=True)
        current=self.variant(mutate,date(2026,10,15))
        expired=self.variant(mutate,date(2026,10,16))
        self.assertIn('data-open-call-until="2026-10-15T23:59:59+03:00"',current)
        self.assertNotIn('id="participation"',expired)
        unapproved=self.variant(lambda c:c['openCall'].update(deadline='2026-10-01',deadlineConfirmed=False))
        self.assertIn('id="participation"',unapproved);self.assertNotIn('2026-10-01',unapproved)
    def test_approved_updates(self):
        def mutate(c):
            c['tickets'].update(status='on_sale',url='https://tickets.example.org/balfest',options=[{'name':'Тестовый билет','price':1500,'confirmed':True}])
            c['venue'].update(confirmed=True,name='Тестовая площадка',address='Тестовый адрес')
            c['contacts']['emailVerified']=True
            c['program']['days'][0]['sessions']=[{'confirmed':True,'time':'12:00','title':'Тестовый блок','hall':'Тестовый зал','level':'Первое знакомство','directionId':'tango'}]
        text=self.variant(mutate)
        self.assertIn('1500 ₽',text);self.assertIn('Тестовая площадка',text);self.assertIn('mailto:hello@balfest.ru',text);self.assertIn('Тестовый блок',text)
        self.assertIn('"@type":"Offer"',text)
    def test_unapproved_entities_hidden(self):
        def mutate(c):
            c['studios']=[{'confirmed':False,'name':'СЕКРЕТНАЯ СТУДИЯ'}]
            c['partners']=[{'confirmed':False,'name':'НЕПОДТВЕРЖДЁННЫЙ ПАРТНЁР'}]
            c['program']['days'][0]['sessions']=[{'confirmed':False,'title':'СЕКРЕТНЫЙ БЛОК'}]
        text=self.variant(mutate)
        for secret in ['СЕКРЕТНАЯ СТУДИЯ','НЕПОДТВЕРЖДЁННЫЙ ПАРТНЁР','СЕКРЕТНЫЙ БЛОК']:self.assertNotIn(secret,text)
    def test_escaping_and_url_validation(self):
        text=self.variant(lambda c:c['about'].update(heading='<script>alert(1)</script>'))
        self.assertNotIn('<script>alert(1)</script>',text);self.assertIn('&lt;script&gt;',text)
        with self.assertRaises(ValueError):self.variant(lambda c:c['contacts'].update(vk='javascript:alert(1)'))
    def test_mobile_and_motion_styles_present(self):
        css=(ROOT/'dist/assets/styles.css').read_text()
        self.assertIn('prefers-reduced-motion:reduce',css)
        self.assertIn('forced-colors:active',css)
        self.assertIn('min-height:44px',css)
        self.assertIn('max-width:599px',css)
        self.assertNotIn('overflow-x:hidden',css)

if __name__=='__main__':unittest.main(verbosity=2)
