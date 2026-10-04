
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
        + quote(query)
        + "&hl=es&gl=ES&ceid=ES:es"
    )

    try:
        root = ET.fromstring(fetch(rss_url, 15))

    except Exception as error:
        print("RSS error:", query, error)
        continue

    for item in root.findall("./channel/item"):

        title = clean(item.findtext("title", ""))
        link = item.findtext("link", "").strip()
        description = clean(item.findtext("description", ""))
        published = item.findtext("pubDate", "")

        if not title or not link:
            continue

        source = get_source(item)
        image = image_from_html(link)

        article_id = (
            "auto-"
            + hashlib.sha1(
                link.encode("utf-8")
            ).hexdigest()[:12]
        )

        article = {
            "id": article_id,
            "title": title,
            "description": description[:420],
            "source": source,
            "date": parse_date(published),
            "category": "Para ti",
            "game": "",
            "url": link,
            "image": image,
        }

        items.append(article)

        if len(items) >= 100:
            break

    if len(items) >= 100:
        break


old = []

try:
    old = json.loads(
        OUT.read_text(encoding="utf-8")
    )
except Exception:
    old = []


seen = set()
merged = []

for news in items + old:

    url = (news.get("url") or "").strip().lower()
    title = (news.get("title") or "").strip().lower()

    key = url or title

    if not key or key in seen:
        continue

    seen.add(key)

    news["category"] = "Para ti"
    news["game"] = ""

    merged.append(news)


merged = merged[:60]

OUT.write_text(
    json.dumps(
        merged,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

print(f"Noticias guardadas: {len(merged)}")
