#!/usr/bin/env python3

import json
import re
import html
import urllib.request
import urllib.parse
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
            timeout=20
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


def get_decoding_params(google_url):

    try:
        parsed = urllib.parse.urlparse(
            google_url
        )

        article_id = parsed.path.split("/")[-1]

        if not article_id:
            return None

        article_url = (
            "https://news.google.com/rss/articles/"
            + article_id
        )

        request = urllib.request.Request(
            article_url,
            headers={
                "User-Agent": "Mozilla/5.0",
                "Accept-Language": "es-ES,es;q=0.9"
            }
        )

        with urllib.request.urlopen(
            request,
            timeout=20
        ) as response:
            page = response.read().decode(
                "utf-8",
                errors="ignore"
            )

        signature_match = re.search(
            r'data-n-a-sg="([^"]+)"',
            page
        )

        timestamp_match = re.search(
            r'data-n-a-ts="([^"]+)"',
            page
        )

        if not signature_match or not timestamp_match:
            print("No se encontraron los parámetros de Google News.")
            return None

        return {
            "id": article_id,
            "signature": signature_match.group(1),
            "timestamp": timestamp_match.group(1)
        }

    except Exception as error:
        print(
            "Error obteniendo parámetros:",
            error
        )

        return None


def decode_google_news_url(google_url):

    params = get_decoding_params(
        google_url
    )

    if not params:
        return None

    article_id = params["id"]
    signature = params["signature"]
    timestamp = params["timestamp"]

    request_data = (
        '["garturlreq",'
        '[["X","X",["X","X"],null,null,1,1,'
        '"US:en",null,1,null,null,null,null,null,0,1],'
        '"X","X",1,[1,1,1],1,1,null,0,0,null,0],'
        f'"{article_id}",'
        f'{timestamp},'
        f'"{signature}"'
        ']'
    )

    batch = [
        [
            "Fbv4je",
            request_data,
            None,
            "generic"
        ]
    ]

    payload = (
        "f.req="
        + urllib.parse.quote(
            json.dumps([batch])
        )
    )

    request = urllib.request.Request(
        "https://news.google.com/_/DotsSplashUi/data/batchexecute",
        data=payload.encode("utf-8"),
        headers={
            "Content-Type":
                "application/x-www-form-urlencoded;charset=UTF-8",
            "User-Agent":
                "Mozilla/5.0",
            "Referer":
                "https://news.google.com/"
        },
        method="POST"
    )

    try:

        with urllib.request.urlopen(
            request,
            timeout=20
        ) as response:

            result = response.read().decode(
                "utf-8",
                errors="ignore"
            )

        match = re.search(
            r'\[\\"garturlres\\",\\"(https?://.*?),',
            result
        )

        if match:

            decoded_url = match.group(1)

            decoded_url = (
                decoded_url
                .replace('\\"', '"')
                .replace("\\/", "/")
            )

            return decoded_url

        print(
            "Google no devolvió la URL original."
        )

    except Exception as error:

        print(
            "Error en batchexecute:",
            error
        )

    return None


def get_original_url(google_url):

    if not google_url:
        return None

    if "news.google.com" not in google_url:
        return google_url

    return decode_google_news_url(
        google_url
    )


def get_article_image(original_url):

    if not original_url:
        return None

    data = download(
        original_url
    )

    if not data:
        return None

    page = data.decode(
        "utf-8",
        errors="ignore"
    )

    return find_image(
        page
    )


def main():

    print("Descargando noticias...")

    data = download(
        RSS_URL
    )

    if not data:

        print(
            "No se pudo descargar el RSS."
        )

        return

    try:

        root = ET.fromstring(
            data
        )

    except Exception as error:

        print(
            "Error leyendo RSS:",
            error
        )

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

        print(
            "Procesando:",
            title
        )

        original_url = get_original_url(
            google_url
        )

        if not original_url:

            print(
                "No se encontró la URL original."
            )

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
            used_images.add(
                image
            )

        article = {
            "title": clean_text(
                title
            ),
            "description": clean_text(
                description
            )[:300],
            "link": original_url,
            "googleLink": google_url,
            "image": image,
            "category": "Para ti",
            "game": "",
            "date": pub_date
        }

        articles.append(
            article
        )

        if len(articles) >= 60:
            break

    unique = []
    seen_titles = set()

    for article in articles:

        key = article["title"].lower().strip()

        if key in seen_titles:
            continue

        seen_titles.add(
            key
        )

        unique.append(
            article
        )

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
