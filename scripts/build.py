#!/usr/bin/env python3
"""Build a portable static site. Python 3.10+, standard library only."""
from __future__ import annotations
import argparse
import hashlib
import html
import json
import re
import shutil
from datetime import date, datetime, time, timedelta, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
MOSCOW = timezone(timedelta(hours=3))
MONTHS = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря']
WEEKDAYS = ['Понедельник','Вторник','Среда','Четверг','Пятница','Суббота','Воскресенье']

def esc(value):
    return html.escape(str(value), quote=True)

def safe_url(value):
    if not isinstance(value, str) or urlparse(value).scheme != 'https' or not urlparse(value).netloc or any(c in value for c in '\n\r<>"'):
        raise ValueError(f'Expected an HTTPS URL: {value!r}')
    return esc(value)

def asset(value):
    value = str(value)
    if not re.fullmatch(r'[a-zA-Z0-9_./-]+', value) or '..' in Path(value).parts or value.startswith('/'):
        raise ValueError(f'Unsafe relative asset path: {value!r}')
    if not (ROOT / 'static' / value).is_file():
        raise ValueError(f'Missing asset: static/{value}')
    return esc(value)

def js_json(value):
    return json.dumps(value, ensure_ascii=False, separators=(',', ':')).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026')

def date_range(start, end):
    if start.month == end.month and start.year == end.year:
        return f'{start.day}–{end.day} {MONTHS[start.month-1]} {start.year}'
    return f'{start.day} {MONTHS[start.month-1]} {start.year} — {end.day} {MONTHS[end.month-1]} {end.year}'

def build(content_path, output, today=None):
    c = json.loads(content_path.read_text(encoding='utf-8'))
    s = c['site']; h = c['hero']; about = c['about']; call = c['openCall']
    tickets = c['tickets']; contacts = c['contacts']; venue = c['venue']
    start = date.fromisoformat(s['startDate']); end = date.fromisoformat(s['endDate'])
    if end < start: raise ValueError('endDate precedes startDate')
    actual_today = today or datetime.now(MOSCOW).date()
    canonical = s['url'].rstrip('/') + '/'
    safe_url(canonical)
    if urlparse(canonical).path != '/': raise ValueError('Site must be hosted at a domain root')
    vk = safe_url(contacts['vk'])
    date_label = date_range(start, end)
    directions = c['directions']
    direction_ids = [d['id'] for d in directions]
    if len(set(direction_ids)) != len(direction_ids): raise ValueError('Duplicate direction IDs')
    call_enabled = bool(call['enabled'])
    deadline = None
    if call.get('deadline') and call.get('deadlineConfirmed'):
        deadline = date.fromisoformat(call['deadline'])
        call_enabled = call_enabled and actual_today <= deadline
    is_sale = tickets['status'] == 'on_sale' and bool(tickets['url'])
    if tickets['status'] == 'on_sale' and not tickets['url']:
        raise ValueError('Ticket sales enabled without an approved URL')
    if is_sale: safe_url(tickets['url'])
    ticket_status = 'Билеты в продаже' if is_sale else 'Билеты скоро в продаже'
    program_status = 'Программа опубликована' if c['program']['status'] == 'published' else 'Программа формируется'
    venues = 'Площадка будет объявлена'
    if venue.get('confirmed'):
        if not venue['name'] or not venue['address']: raise ValueError('Confirmed venue requires name and address')
        venues = venue['name']
    # Escape every text input; only fragments authored by this builder are HTML.
    tokens = {
        'TITLE': esc(s['title']), 'DESCRIPTION': esc(s['description']),
        'CANONICAL': esc(canonical), 'OG_IMAGE': esc(canonical+'assets/og-image.jpg'),
        'NAME': esc(s['name']), 'CITY': esc(s['city']), 'YEAR': esc(s['year']),
        'BACKGROUND': esc(c['theme']['background']), 'DATE_RANGE': esc(date_label),
        'HERO_EYEBROW': esc(h['eyebrow']), 'HERO_TAGLINE': esc(h['tagline']),
        'HERO_ACCENT': esc(h['taglineAccent']), 'HERO_DESCRIPTION': esc(h['description']),
        'HERO_PRIMARY': esc(h['primaryLabel']), 'HERO_SECONDARY': esc(h['secondaryLabel']),
        'HERO_ALT': esc(h['imageAlt']), 'HERO_CAPTION': esc(h['imageCaption']),
        'ABOUT_HEADING': esc(about['heading']), 'ABOUT_ACCENT': esc(about['accent']),
        'ABOUT_LEAD': esc(about['lead']), 'ABOUT_PARAGRAPHS': ''.join(f'<p>{esc(p)}</p>' for p in about['paragraphs']),
        'DIRECTIONS_NOTE': esc(c['directionsNote']),
        'PROGRAM_INTRO': esc(c['program']['intro']), 'VENUE_STATUS': esc(venues),
        'PROGRAM_STATUS': program_status, 'TICKETS_STATUS': ticket_status, 'TICKETS_HEADING': 'До встречи' if is_sale else 'Ваш танец',
        'TICKETS_ACCENT': 'на БАЛФЕСТ.' if is_sale else 'начнётся здесь.',
        'TICKETS_DESCRIPTION': esc(tickets['description']), 'VK_URL': vk,
        'PARTNERS_HEADING': esc(c['collaboration']['heading']), 'PARTNERS_ACCENT': esc(c['collaboration']['accent']),
        'PARTNERS_DESCRIPTION': esc(c['collaboration']['description']), 'PARTNERS_LABEL': esc(c['collaboration']['label']),
        'PARTNERS_URL': safe_url(c['collaboration']['url']),
        'PARTNER_FORMATS': ''.join(f'<li>{esc(x)}</li>' for x in c['collaboration']['formats']),
        'OPEN_CALL_NAV': '<a href="#participation">Участие</a>' if call_enabled else '',
        'PIN_ICON': '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.4"><path d="M19 10c0 5-7 11-7 11S5 15 5 10a7 7 0 1 1 14 0Z"/><circle cx="12" cy="10" r="2.5"/></svg>',
    }
    tokens['AUDIENCES'] = ''.join(f'<article class="audience-card"><span class="audience-number">{esc(a["number"])}</span><h3>{esc(a["title"])}</h3><p>{esc(a["text"])}</p></article>' for a in about['audiences'])
    tokens['DIRECTIONS'] = ''.join(
        f'<details class="direction-card" id="direction-{esc(d["id"])}"><summary><span class="direction-top"><span class="direction-category">{esc(d["category"])}</span><span class="direction-number">{i:02d}</span></span><span class="direction-name">{esc(d["name"]).replace(chr(10),"<br>")}</span><span class="direction-hint">О направлении <span class="direction-toggle" aria-hidden="true">+</span></span></summary><p>{esc(d["description"])}</p></details>'
        for i,d in enumerate(directions,1))
    days = []
    program_dates = []
    for day in c['program']['days']:
        d = date.fromisoformat(day['date']); program_dates.append(d)
        if not start <= d <= end: raise ValueError('Program date outside festival dates')
        sessions = []
        for session in day.get('sessions', []):
            if not session.get('confirmed'): continue
            if session.get('directionId') not in direction_ids: raise ValueError('Unknown session directionId')
            if not re.fullmatch(r'([01]\d|2[0-3]):[0-5]\d', session['time']): raise ValueError('Session time must be HH:MM')
            extra = ' · '.join(str(session.get(x,'')) for x in ['hall','level'] if session.get(x))
            sessions.append(f'<li><time datetime="{d.isoformat()}T{esc(session["time"])}:00+03:00">{esc(session["time"])}</time><strong>{esc(session["title"])}</strong><span>{esc(extra)}</span></li>')
        day_text = '<ul class="session-list">' + ''.join(sessions) + '</ul>' if sessions else '<p>Программа формируется</p>'
        days.append(f'<article class="day-card"><div class="day-top">{WEEKDAYS[d.weekday()]}<time datetime="{d.isoformat()}">{MONTHS[d.month-1]} {d.year}</time></div><h3 aria-label="{d.day} {MONTHS[d.month-1]}">{d.day:02d}</h3>{day_text}</article>')
    if len(set(program_dates)) != len(program_dates): raise ValueError('Duplicate program dates')
    tokens['PROGRAM_DAYS'] = ''.join(days)
    tokens['VENUE_CONTENT'] = '<strong>Санкт-Петербург · площадка будет объявлена</strong><p>Адрес и информация о проезде появятся после подтверждения.</p>'
    if venue.get('confirmed'):
        tokens['VENUE_CONTENT'] = f'<strong>{esc(venue["name"])}</strong><p>{esc(venue["address"])}</p><p>{esc(venue.get("description",""))}</p>'
        if venue.get('mapUrl'): tokens['VENUE_CONTENT'] += f'<a class="text-link" href="{safe_url(venue["mapUrl"])}" target="_blank" rel="noopener noreferrer">Открыть карту ↗</a>'
    tokens['OPEN_CALL_SECTION'] = ''
    if call_enabled:
        deadline_attr = f' data-open-call-until="{deadline.isoformat()}T23:59:59+03:00"' if deadline else ''
        deadline_html = f'<p class="status-badge">До {deadline.day} {MONTHS[deadline.month-1]} {deadline.year}</p>' if deadline else ''
        poster = asset('assets/'+call['image'])
        tokens['OPEN_CALL_SECTION'] = f'''<section class="section open-call-section" id="participation" aria-labelledby="call-title"{deadline_attr}><div class="container open-call-layout"><div class="open-call-copy"><p class="eyebrow">04 / Участие в программе · Open Call</p><h2 id="call-title">{esc(call['heading'])}<br><em>{esc(call['accent'])}</em></h2><p>{esc(call['description'])}</p>{deadline_html}<p class="small-note">{esc(call['prompt'])}</p><a class="button button-gold" href="{safe_url(call['url'])}" target="_blank" rel="noopener noreferrer">{esc(call['label'])}<span aria-hidden="true">↗</span></a></div><figure class="call-figure"><a href="assets/open-call-full.webp" target="_blank" rel="noopener noreferrer" aria-label="Открыть афишу Open Call в полном размере"><img src="{poster}" srcset="assets/open-call-768.webp 768w, assets/open-call-1280.webp 1280w, assets/open-call-full.webp 1672w" sizes="(max-width: 767px) calc(100vw - 36px), 55vw" width="1672" height="941" alt="{esc(call['imageAlt'])}" loading="lazy" decoding="async"></a><figcaption><span>Рабочая художественная афиша</span><a class="text-link" href="assets/open-call-full.webp" target="_blank" rel="noopener noreferrer">Открыть крупнее <span aria-hidden="true">↗</span></a></figcaption></figure></div></section>'''
    tokens['TICKET_ACTION'] = f'<a class="button button-gold" href="{safe_url(tickets["url"]) if is_sale else vk}" target="_blank" rel="noopener noreferrer">{esc(tickets["label"]) if is_sale else "Следить за новостями в VK"}<span aria-hidden="true">↗</span></a>'
    tokens['TICKET_OPTIONS'] = ''
    approved_options = [o for o in tickets.get('options',[]) if o.get('confirmed')]
    if is_sale and approved_options:
        options = []
        for o in approved_options:
            if not isinstance(o['price'],(int,float)) or o['price']<0: raise ValueError('Ticket price must be a nonnegative number')
            options.append(f'<li><span>{esc(o["name"])}</span><strong>{esc(o["price"])} ₽</strong></li>')
        tokens['TICKET_OPTIONS'] = '<ul class="ticket-options">'+''.join(options)+'</ul>'
    tokens['STUDIOS'] = ''
    studios = []
    for studio in c.get('studios',[]):
        if not studio.get('confirmed'): continue
        if any(i not in direction_ids for i in studio.get('directionIds',[])): raise ValueError('Unknown studio directionId')
        studios.append(f'<article class="studio-card"><h3>{esc(studio["name"])}</h3><p>{esc(studio.get("description",""))}</p><a class="text-link" href="{safe_url(studio["url"])}" target="_blank" rel="noopener noreferrer">О студии ↗</a></article>')
    if studios: tokens['STUDIOS'] = '<h3 class="lead" style="margin-top:45px">Участники фестиваля</h3><div class="studio-grid">'+''.join(studios)+'</div>'
    tokens['PARTNER_LOGOS'] = ''
    partners = []
    for partner in c.get('partners',[]):
        if not partner.get('confirmed'): continue
        logo = f'<img src="{asset(partner["logo"])}" alt="{esc(partner["name"])}" loading="lazy" decoding="async">' if partner.get('logo') else ''
        partners.append(f'<a class="partner-logo" href="{safe_url(partner["url"])}" target="_blank" rel="noopener noreferrer">{logo}<p>{esc(partner["name"])}</p></a>')
    if partners: tokens['PARTNER_LOGOS'] = '<div class="partners-grid">'+''.join(partners)+'</div>'
    tokens['FAQ'] = ''.join(f'<details><summary>{esc(f["question"])}<span aria-hidden="true">+</span></summary><p>{esc(f["answer"])}</p></details>' for f in c['faq'])
    tokens['CONTACT_EMAIL'] = ''
    if contacts.get('emailVerified'):
        if not re.fullmatch(r'[^\s<>@]+@[^\s<>@]+\.[^\s<>@]+',contacts['email']): raise ValueError('Invalid contact email')
        tokens['CONTACT_EMAIL'] = f'<a href="mailto:{esc(contacts["email"])}">{esc(contacts["email"])}</a>'
    tokens['SOCIALS'] = ''.join(f'<a href="{safe_url(x["url"])}" target="_blank" rel="noopener noreferrer">{esc(x["name"])}</a>' for x in contacts.get('socials',[]))
    tokens['VERIFICATION'] = ''
    analytics = c['analytics']
    for key, name in [('googleSiteVerification','google-site-verification'),('yandexVerification','yandex-verification')]:
        if analytics.get(key): tokens['VERIFICATION'] += f'<meta name="{name}" content="{esc(analytics[key])}">\n'
    if analytics['enabled'] and not re.fullmatch(r'\d+',str(analytics.get('yandexMetrikaId',''))): raise ValueError('Enabled analytics requires numeric Yandex Metrika ID')
    tokens['ANALYTICS_SCRIPT'] = '<script type="application/json" id="analytics-config">'+js_json({'enabled':analytics['enabled'],'yandexMetrikaId':analytics['yandexMetrikaId']})+'</script>' if analytics['enabled'] else ''
    schema = {'@context':'https://schema.org','@type':'Event','name':s['name'],'alternateName':s['latinName'],'description':s['description'],'url':canonical,'startDate':s['startDate'],'endDate':s['endDate'],'eventAttendanceMode':'https://schema.org/OfflineEventAttendanceMode','eventStatus':'https://schema.org/EventScheduled','inLanguage':'ru','image':[canonical+'assets/og-image.jpg'],'location':{'@type':'City','name':s['city'],'address':{'@type':'PostalAddress','addressLocality':s['city'],'addressCountry':'RU'}},'organizer':{'@type':'Organization','name':'БАЛФЕСТ','url':canonical,'sameAs':[contacts['vk']]}}
    if venue.get('confirmed'):
        schema['location'] = {'@type':'Place','name':venue['name'],'address':{'@type':'PostalAddress','streetAddress':venue['address'],'addressLocality':s['city'],'addressCountry':'RU'}}
    if is_sale and approved_options:
        schema['offers'] = [{'@type':'Offer','name':o['name'],'url':tickets['url'],'price':o['price'],'priceCurrency':'RUB'} for o in approved_options]
    tokens['EVENT_JSON'] = js_json(schema)
    if output.resolve() in [ROOT.resolve(), (ROOT/'source').resolve(), (ROOT/'static').resolve()]: raise ValueError('Unsafe output directory')
    output.mkdir(parents=True, exist_ok=True)
    shutil.copytree(ROOT/'static',output,dirs_exist_ok=True)
    theme = c['theme']
    for color in theme.values():
        if not re.fullmatch(r'#[0-9a-fA-F]{6}',color): raise ValueError('Theme colors must be #RRGGBB')
    (output/'assets/theme.css').write_text(':root{'+''.join(f'--{k}:{v};' for k,v in [('bg',theme['background']),('surface',theme['surface']),('gold',theme['gold']),('text',theme['text']),('muted',theme['muted'])])+'}\n',encoding='utf-8')
    for key, filename in [('CSS_URL','styles.css'),('JS_URL','site.js'),('THEME_URL','theme.css')]:
        digest=hashlib.sha256((output/'assets'/filename).read_bytes()).hexdigest()[:10]
        tokens[key]=f'assets/{filename}?v={digest}'
    template=(ROOT/'source/index.template.html').read_text(encoding='utf-8')
    used=set(re.findall(r'\{\{([A-Z_]+)\}\}',template))
    if used - tokens.keys(): raise ValueError('Missing tokens: '+', '.join(sorted(used-tokens.keys())))
    page=re.sub(r'\{\{([A-Z_]+)\}\}',lambda m:tokens[m[1]],template)
    (output/'index.html').write_text(page,encoding='utf-8')
    (output/'robots.txt').write_text(f'User-agent: *\nAllow: /\n\nSitemap: {canonical}sitemap.xml\n',encoding='utf-8')
    (output/'sitemap.xml').write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9"><url><loc>'+esc(canonical)+'</loc><lastmod>'+actual_today.isoformat()+'</lastmod></url></urlset>\n',encoding='utf-8')
    error='''<!doctype html><html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>Страница не найдена — БАЛФЕСТ IV</title><link rel="stylesheet" href="/assets/styles.css"><link rel="stylesheet" href="/assets/theme.css"><link rel="icon" href="/assets/favicon.svg"></head><body><main class="error-page"><div class="error-box"><p class="eyebrow">БАЛФЕСТ IV</p><h1>404</h1><h2>Этот маршрут ещё не проложен.</h2><p>Вернитесь на главную, чтобы узнать о фестивале.</p><a class="button button-gold" href="/">На главную <span aria-hidden="true">↗</span></a></div></main></body></html>'''
    (output/'404.html').write_text(error,encoding='utf-8')
    return {'output':str(output),'files':sum(1 for p in output.rglob('*') if p.is_file()),'openCallVisible':call_enabled,'tickets':ticket_status,'dateRange':date_label}

if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--content',type=Path,default=ROOT/'source/content.json')
    parser.add_argument('--output',type=Path,default=ROOT/'dist')
    parser.add_argument('--today',type=date.fromisoformat,help='QA: override Moscow date (YYYY-MM-DD)')
    args=parser.parse_args()
    print(json.dumps(build(args.content,args.output,args.today),ensure_ascii=False))
