#!/usr/bin/env python3

import json
import re
import html
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

RSS_URL = "https://news.google.com/rss/search?q=videojuegos+gaming+videojuegos&hl=es&gl=ES&ceid=ES:es"

OUTPUT_FILE = "news.json"

FALLBACK_IMAGE = "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=1200&q=80"


def download(url):
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        with urllib.request.urlopen(request, timeout=15) as response:
            return response.read()

    except Exception:
        return None


def clean_text(text):
    if not text:
        return ""

    text = html.unescape(text)
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


def find_image(text):
    if not text:
        return None

    patterns = [
        r'<img[^>]+src=["\']([^"\']+)["\']',
        r'<img[^>]+src=([^ >]+)',
    ]

    for pattern in patterns:
        match = re.search(pattern, text, re.IGNORECASE)

        if match:
            image = html.unescape(match.group(1))

            if image.startswith("http"):
                return image

    return None


def get_original_image(url):
    data = download(url)

    if not data:
        return None

    try:
        page = data.decode("utf-8", errors="ignore")
    except Exception:
        return None

    patterns = [
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
    ]

    for pattern in patterns:
        match = re.search(pattern, page, re.IGNORECASE)

        if match:
            image = html.unescape(match.group(1))

            if image.startswith("http"):
                return image

    return find_image(page)


def get_text(element, tag):
    found = element.find(tag)

    if found is not None and found.text:
        return found.text.strip()

    return ""


def main():

    data = download(RSS_URL)

    if not data:
        print("No se pudo descargar el RSS.")
        return

    try:
        root = ET.fromstring(data)
    except Exception as error:
        print("Error leyendo RSS:", error)
        return

    articles = []

    for item in root.findall(".//item"):

        title = get_text(item, "title")
        link = get_text(item, "link")
        pub_date = get_text(item, "pubDate")
        description = get_text(item, "description")

        if not title or not link:
            continue

        image = None

        # Buscar imagen dentro de la descripción del RSS
        image = find_image(description)

        # Buscar imágenes en media:content / media:thumbnail
        if image is None:

            for child in item:
                tag = child.tag.lower()

                if "content" in tag or "thumbnail" in tag or "enclosure" in tag:

                    url = child.attrib.get("url")

                    if url and url.startswith("http"):
                        image = url
                        break

        # Intentar conseguir la imagen original
        if image is None:
            image = get_original_image(link)

        # Imagen de emergencia
        if image is None:
            image = FALLBACK_IMAGE

        article = {
            "title": clean_text(title),
            "description": clean_text(description)[:300],
            "link": link,
            "image": image,
            "category": "Para ti",
            "game": "",
            "date": pub_date
        }

        articles.append(article)

    # Eliminar noticias repetidas
    unique = []
    seen = set()

    for article in articles:

        key = article["title"].lower().strip()

        if key in seen:
            continue

        seen.add(key)
        unique.append(article)

    # Máximo 60 noticias
    unique = unique[:60]

    # Si ya existe news.json, conservar noticias anteriores
    try:

        with open(OUTPUT_FILE, "r", encoding="utf-8") as file:
            old_news = json.load(file)

            if isinstance(old_news, list):

                existing_titles = {
                    article.get("title", "").lower().strip()
                    for article in unique
                }

                for old_article in old_news:

                    title = old_article.get("title", "").lower().strip()

                    if title and title not in existing_titles:

                        if not old_article.get("image"):
                            old_article["image"] = FALLBACK_IMAGE

                        unique.append(old_article)

                        existing_titles.add(title)

    except Exception:
        pass

    unique = unique[:60]

    with open(OUTPUT_FILE, "w", encoding="utf-8") as file:

        json.dump(
            unique,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(f"Noticias guardadas: {len(unique)}")


if __name__ == "__main__":
    main()
