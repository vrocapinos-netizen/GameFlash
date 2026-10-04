#!/usr/bin/env python3

"""Actualizador automático de noticias de GameFlash.

Todas las noticias aparecen en "Para ti".
Intenta obtener imágenes desde RSS y desde la página original.
"""

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
    "últimas noticias videojuegos",
    "nuevos juegos videojuegos",
    "actualizaciones videojuegos",
    "lanzamientos videojuegos",
    "PlayStation Xbox Nintendo PC videojuegos",
    "industria videojuegos",
    "videojuegos novedades",
]

UA = (
    "Mozilla/5.0 (compatible; GameFlashBot/1.0; "
    "+https://github.com/)"
)

# Imágenes de respaldo.
FALLBACK_IMAGE = (
    "https://images.unsplash.com/"
    "photo-1542751371-adc38448a05e"
    "?auto=format&fit=crop&w=1200&q=80"
)


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
    text = unescape(
        re.sub(r"<[^>]+>", " ", text or "")
    )
    return re.sub(r"\s+", " ", text).strip()


def valid_image(url):
    if not url:
        return ""

    url = unescape(url).strip()

    if not url.startswith(("http://", "https://")):
        return ""

    return url


def image_from_rss(item):
    """Busca imágenes que vengan directamente dentro del RSS."""

    # media:content
    for element in item.iter():
        tag = element.tag.lower()

        if (
            tag.endswith("content")
            or tag.endswith("thumbnail")
            or tag.endswith("enclosure")
        ):
            url = element.attrib.get("url", "")

            if valid_image(url):
                return valid_image(url)

    # Imagen dentro de la descripción HTML
    description = item.findtext("description", "")

    match = re.search(
        r'<img[^>]+src=["\']([^"\']+)',
        description,
        re.I,
    )

    if match:
        image = valid_image(match.group(1))

        if image:
            return image

    return ""


def image_from_html(url):
    """Busca la imagen principal de la página."""

    try:
        raw = fetch(url, 10).decode(
            "utf-8",
            "ignore"
        )[:1000000]

        # Open Graph
        patterns = [
            r'<meta[^>]+property=["\']og:image["\']'
            r'[^>]+content=["\']([^"\']+)',

            r'<meta[^>]+content=["\']([^"\']+)'
            r'[^>]+property=["\']og:image["\']',

            r'<meta[^>]+name=["\']twitter:image["\']'
            r'[^>]+content=["\']([^"\']+)',

            r'<meta[^>]+content=["\']([^"\']+)'
            r'[^>]+name=["\']twitter:image["\']',
        ]

        for pattern in patterns:
            match = re.search(
                pattern,
                raw,
                re.I,
            )

            if match:
                image = valid_image(
                    match.group(1)
                )

                if image:
                    return image

    except Exception as error:
        print(
            "No se pudo obtener imagen:",
            error
        )

    return ""


def get_image(item, link):
    """Intenta conseguir la mejor imagen disponible."""

    image = image_from_rss(item)

    if image:
        return image

    image = image_from_html(link)

    if image:
        return image

    return FALLBACK_IMAGE


def parse_date(date_text):
    try:
        return (
            parsedate_to_datetime(date_text)
            .astimezone(timezone.utc)
            .strftime("%d %b %Y")
        )
    except Exception:
        return datetime.now(
            timezone.utc
        ).strftime("%d %b %Y")


def get_source(item):
    source = item.find("source")

    if source is not None and source.text:
        return clean(source.text)

    return "Google News"


# ---------------------------------------------------------
# OBTENER NOTICIAS
# ---------------------------------------------------------

items = []

for query in QUERIES:

    rss_url = (
        "https://news.google.com/rss/search?q="
        + quote(query)
        + "&hl=es&gl=ES&ceid=ES:es"
    )

    try:
        root = ET.fromstring(
            fetch(rss_url, 15)
        )

    except Exception as error:
        print(
            "Error RSS:",
            query,
            error
        )
        continue

    for item in root.findall(
        "./channel/item"
    ):

        title = clean(
            item.findtext(
                "title",
                ""
            )
        )

        link = (
            item.findtext(
                "link",
                ""
            )
            .strip()
        )

        description = clean(
            item.findtext(
                "description",
                ""
            )
        )

        published = item.findtext(
            "pubDate",
            ""
        )

        if not title or not link:
            continue

        source = get_source(item)

        image = get_image(
            item,
            link
        )

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

            "date": parse_date(
                published
            ),

            # Todas las noticias son Para ti.
            "category": "Para ti",

            # Ya no usamos categorías
            # de juegos.
            "game": "",

            "url": link,

            "image": image,
        }

        items.append(article)

        if len(items) >= 100:
            break

    if len(items) >= 100:
        break


# ---------------------------------------------------------
# CONSERVAR NOTICIAS ANTERIORES
# ---------------------------------------------------------

old = []

try:
    old = json.loads(
        OUT.read_text(
            encoding="utf-8"
        )
    )

except Exception:
    old = []


seen = set()
merged = []

for news in items + old:

    url = (
        news.get("url") or ""
    ).strip().lower()

    title = (
        news.get("title") or ""
    ).strip().lower()

    key = url or title

    if not key:
        continue

    if key in seen:
        continue

    seen.add(key)

    # Forzamos Para ti.
    news["category"] = "Para ti"
    news["game"] = ""

    # Si una noticia antigua no tiene
    # imagen, le ponemos una de respaldo.
    if not news.get("image"):
        news["image"] = FALLBACK_IMAGE

    merged.append(news)


# Máximo 60 noticias.
merged = merged[:60]


# ---------------------------------------------------------
# GUARDAR
# ---------------------------------------------------------

OUT.write_text(
    json.dumps(
        merged,
        ensure_ascii=False,
        indent=2,
    ),
    encoding="utf-8",
)

print(
    f"Noticias guardadas: {len(merged)}"
)
```
