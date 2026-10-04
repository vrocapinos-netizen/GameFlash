#!/usr/bin/env python3

import json
import re
import html
import urllib.request
import urllib.parse
import xml.etree.ElementTree as ET

OUTPUT_FILE = "news.json"

RSS_URL = (
    "https://news.google.com/rss/search?"
    "q=videojuegos+gaming+PlayStation+Xbox+Nintendo+PC"
    "&hl=es&gl=ES&ceid=ES:es"
)


def download(url):
    try:
        request = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Mozilla/5.0"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=15
        ) as response:
            return response.read()

    except Exception as error:
        print("Error descargando:", url)
        print(error)
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
        r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
        r'<meta[^>]+name=["\']twitter:image["\'][^>]+content=["\']([^"\']+)["\']',
        r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+name=["\']twitter:image["\']',
    ]

    for pattern in patterns:
        match = re.search(
            pattern,
            text,
            re.IGNORECASE
        )

        if match:
            image = html.unescape(match.group(1))

            if image.startswith("http"):
                return image

    return None


def get_original_url(google_url):

    try:
        data = download(google_url)

        if not data:
            return None

        page = data.decode(
            "utf-8",
            errors="ignore"
        )

        # Buscar una URL http/https dentro de la respuesta
        urls = re.findall(
            r'https?://[^\s"<>]+',
            page
        )

        for url in urls:

            url = html.unescape(url)

            # Ignorar URLs de Google
            if "google.com" in url:
                continue

            if "googleusercontent.com" in url:
                continue

            if url.startswith("http"):
                return url

    except Exception as error:
        print("Error buscando URL original:", error)

    return None


def get_article_image(original_url):

    data = download(original_url)

    if not data:
        return None

    page = data.decode(
        "utf-8",
        errors="ignore"
    )

    return find_image(page)


def main():

    print("Descargando noticias...")

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
    used_images = set()

    for item in root.findall(".//item"):

        title = item.findtext(
            "title",
            ""
        ).strip()

        google_url = item.findtext(
            "link",
            ""
        ).strip()

        pub_date = item.findtext(
            "pubDate",
            ""
        ).strip()

        description = item.findtext(
            "description",
            ""
        ).strip()

        if not title or not google_url:
            continue

        print("Procesando:", title)

        original_url = get_original_url(
            google_url
        )

        if not original_url:
            print("No se encontró la URL original.")
            continue

        print(
            "URL original:",
            original_url
        )

        image = get_article_image(
            original_url
        )

        if not image:
            image = find_image(
                description
            )

        if image in used_images:
            print(
                "Imagen repetida, descartada."
            )
            image = ""

        if image:
            used_images.add(image)

        article = {
            "title": clean_text(title),
            "description": clean_text(description)[:300],
            "link": original_url,
            "googleLink": google_url,
            "image": image,
            "category": "Para ti",
            "game": "",
            "date": pub_date
        }

        articles.append(article)

        if len(articles) >= 60:
            break

    unique = []
    seen_titles = set()

    for article in articles:

        key = article["title"].lower().strip()

        if key in seen_titles:
            continue

        seen_titles.add(key)
        unique.append(article)

    with open(
        OUTPUT_FILE,
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            unique,
            file,
            ensure_ascii=False,
            indent=2
        )

    print("--------------------------------")
    print(
        f"Noticias guardadas: {len(unique)}"
    )

    print(
        "Noticias con imagen:",
        sum(
            1
            for article in unique
            if article.get("image")
        )
    )

    print("--------------------------------")


if __name__ == "__main__":
    main()
