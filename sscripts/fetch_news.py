```python
#!/usr/bin/env python3

from urllib.request import Request, urlopen
from urllib.parse import quote
from xml.etree import ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from html import unescape
from pathlib import Path
import json
import re
import hashlib

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "news.json"

QUERIES = [
    "noticias videojuegos",
    "últimas noticias gaming",
    "nuevos juegos videojuegos",
    "actualizaciones videojuegos",
    "lanzamientos videojuegos",
    "PlayStation Xbox Nintendo PC videojuegos",
    "industria videojuegos",
    "videojuegos novedades",
]

UA = "Mozilla/5.0 (compatible; GameFlashBot/1.0; +https://github.com/)"


def fetch(url, timeout=15):
    req = Request(
        url,
        headers={
            "User-Agent": UA,
            "Accept": "text/html,application/rss+xml",
        },
    )
    with urlopen(req, timeout=timeout) as response:
        return response.read()


def clean(text):
    text = unescape(re.sub(r"<[^>]+>", " ", text or ""))
    return re.sub(r"\s+", " ", text).strip()


def image_from_html(url):
    try:
        raw = fetch(url, 10).decode("utf-8", "ignore")[:800000]

        match = re.search(
            r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)',
            raw,
            re.I,
        )

        if match:
            return unescape(match.group(1))

        match = re.search(
            r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)',
            raw,
            re.I,
        )

        if match:
            return unescape(match.group(1))

    except Exception:
        pass

    return ""


def parse_date(date_text):
    try:
        return (
            parsedate_to_datetime(date_text)
            .astimezone(timezone.utc)
            .strftime("%d %b %Y")
        )
    except Exception:
        return datetime.now(timezone.utc).strftime("%d %b %Y")


def get_source(item):
    source_element = item.find("source")

    if source_element is not None and source_element.text:
        return clean(source_element.text)

    return "Google News"


items = []

for query in QUERIES:

    rss_url = (
        "https://news.google.com/rss/search?q="
```
