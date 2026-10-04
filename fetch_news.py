#!/usr/bin/env python3
"""Actualiza news.json sin Node ni API key.
Usa feeds RSS de Google News, obtiene metadatos de las páginas originales
para la imagen y deduplica por URL/título.
"""
from urllib.request import Request, urlopen
from urllib.parse import quote
from xml.etree import ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
import json, re, time

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'news.json'

QUERIES=[
    'videojuegos gaming GTA 6 PlayStation Xbox Nintendo PC',
    'Fortnite Minecraft Roblox Call of Duty Pokémon Zelda',
    'Resident Evil The Witcher Cyberpunk Elden Ring',
    'Nintendo Switch 2 PS5 Xbox Series videojuegos',
    'Steam juegos PC lanzamiento videojuegos',
]

UA='Mozilla/5.0 (compatible; GameFlashBot/1.0; +https://github.com/)'

# Imágenes de respaldo por juego; se usan solo si la noticia no expone una imagen.
FALLBACK={
 'gta 6':'https://cdn.cloudflare.steamstatic.com/steam/apps/271590/library_hero.jpg',
 'gta vi':'https://cdn.cloudflare.steamstatic.com/steam/apps/271590/library_hero.jpg',
 'fortnite':'https://cdn.cloudflare.steamstatic.com/steam/apps/1506830/library_hero.jpg',
 'minecraft':'https://cdn.cloudflare.steamstatic.com/steam/apps/1890860/library_hero.jpg',
 'roblox':'https://tr.rbxcdn.com/180DAY-4c6e2b4b4a1e2f7f1f1f0d5f3e0f7f5f/768/432/Image/Webp/noFilter',
 'call of duty':'https://cdn.cloudflare.steamstatic.com/steam/apps/1938090/library_hero.jpg',
 'resident evil':'https://cdn.cloudflare.steamstatic.com/steam/apps/883710/library_hero.jpg',
 'cyberpunk':'https://cdn.cloudflare.steamstatic.com/steam/apps/1091500/library_hero.jpg',
 'the witcher':'https://cdn.cloudflare.steamstatic.com/steam/apps/292030/library_hero.jpg',
 'elden ring':'https://cdn.cloudflare.steamstatic.com/steam/apps/1245620/library_hero.jpg',
 'helldivers':'https://cdn.cloudflare.steamstatic.com/steam/apps/553850/library_hero.jpg',
 'apex legends':'https://cdn.cloudflare.steamstatic.com/steam/apps/1172470/library_hero.jpg',
 'pubg':'https://cdn.cloudflare.steamstatic.com/steam/apps/578080/library_hero.jpg',
}

def fetch(url, timeout=12):
    req=Request(url,headers={'User-Agent':UA,'Accept':'text/html,application/rss+xml'})
    with urlopen(req,timeout=timeout) as r:return r.read()

def clean(s):
    s=unescape(re.sub(r'<[^>]+>',' ',s or ''))
    return re.sub(r'\s+',' ',s).strip()

def image_from_html(url):
    try:
        raw=fetch(url,10).decode('utf-8','ignore')[:800000]
        m=re.search(r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',raw,re.I)
        if not m:m=re.search(r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',raw,re.I)
        if m:return unescape(m.group(1))
    except Exception: pass
    return ''

def parse_date(s):
    try:return parsedate_to_datetime(s).astimezone(timezone.utc).strftime('%d %b %Y')
    except Exception:
        return datetime.now(timezone.utc).strftime('%d %b %Y')

def detect_game(title,desc):
    t=(title+' '+desc).lower()
    for key in sorted(FALLBACK,key=len,reverse=True):
        if key in t:return key.title()
    return 'Gaming'

def fallback_image(game):
    g=game.lower()
    for key,url in FALLBACK.items():
        if key in g:return url
    return ''

items=[]
for q in QUERIES:
    rss='https://news.google.com/rss/search?q='+quote(q)+'&hl=es&gl=ES&ceid=ES:es'
    try:
        root=ET.fromstring(fetch(rss,15))
    except Exception as e:
        print('RSS error',q,e);continue
    for item in root.findall('./channel/item'):
        title=clean(item.findtext('title',''))
        link=item.findtext('link','').strip()
        desc=clean(item.findtext('description',''))
        pub=item.findtext('pubDate','')
        source_el=item.find('source')
        source=clean(source_el.text if source_el is not None else 'Google News')
        if not title or not link:continue
        game=detect_game(title,desc)
        image=image_from_html(link)
        if not image:image=fallback_image(game)
        items.append({'id':'auto-'+__import__('hashlib').sha1(link.encode('utf-8')).hexdigest()[:12], 'title':title, 'description':desc[:420], 'source':source, 'date':parse_date(pub), 'category':'Gaming', 'game':game, 'url':link, 'image':image})
        if len(items)>=80:break
    if len(items)>=80:break

old=[]
try:old=json.loads(OUT.read_text(encoding='utf-8'))
except Exception:pass
seen=set(); merged=[]
for n in items+old:
    key=(n.get('url') or '').strip().lower() or (n.get('title') or '').strip().lower()
    if not key or key in seen:continue
    seen.add(key);merged.append(n)
# Keep fresh automatic items first, then seed items to avoid empty feed on source outages.
merged=merged[:60]
OUT.write_text(json.dumps(merged,ensure_ascii=False,indent=2),encoding='utf-8')
print(f'Noticias guardadas: {len(merged)}')
