import json
import re
import time
import html
import requests
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from urllib.parse import urlparse


RSS_URL = (
    "https://news.google.com/rss/search?"
    "q=videojuegos+gaming+PlayStation+Xbox+Nintendo+PC"
    "&hl=es&gl=ES&ceid=ES:es"
)

MAX_NEWS = 60

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/154.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "es-ES,es;q=0.9,en;q=0.8",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}


def clean_text(text):
    if not text:
        return ""

    text = html.unescape(text)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def make_absolute_url(image_url, article_url):
    if not image_url:
        return None

    image_url = image_url.strip()

    if image_url.startswith("//"):
        return "https:" + image_url

    if image_url.startswith("/"):
        parsed = urlparse(article_url)

        return (
            parsed.scheme
            + "://"
            + parsed.netloc
            + image_url
        )

    if image_url.startswith("http://"):
        return image_url

    if image_url.startswith("https://"):
        return image_url

    return None


def valid_image_url(url):
    if not url:
        return False

    url = url.lower()

    if url.endswith(".svg"):
        return False

    if url.endswith(".ico"):
        return False

    return (
        url.startswith("http://")
        or url.startswith("https://")
    )


def decode_google_news_url(url):
    if not url:
        return None

    if not url.startswith("https://news.google.com"):
        return url

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15,
            allow_redirects=True
        )

        final_url = response.url

        if (
            final_url
            and "news.google.com" not in final_url
        ):
            return final_url

    except Exception as e:
        print("⚠️ Error descodificando:", e)

    return url


def get_article_image(article_url):
    try:
        response = requests.get(
            article_url,
            headers=HEADERS,
            timeout=15,
            allow_redirects=True
        )

        if response.status_code != 200:
            print(
                "⚠️ Error HTTP:",
                response.status_code
            )
            return None

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # Open Graph
        meta = soup.find(
            "meta",
            property="og:image"
        )

        if meta and meta.get("content"):

            image = make_absolute_url(
                meta.get("content"),
                article_url
            )

            if valid_image_url(image):
                return image

        # Twitter
        meta = soup.find(
            "meta",
            attrs={"name": "twitter:image"}
        )

        if meta and meta.get("content"):

            image = make_absolute_url(
                meta.get("content"),
                article_url
            )

            if valid_image_url(image):
                return image

        # Twitter property
        meta = soup.find(
            "meta",
            attrs={"property": "twitter:image"}
        )

        if meta and meta.get("content"):

            image = make_absolute_url(
                meta.get("content"),
                article_url
            )

            if valid_image_url(image):
                return image

        # JSON-LD
        scripts = soup.find_all(
            "script",
            type="application/ld+json"
        )

        for script in scripts:

            try:
                data = json.loads(
                    script.string
                    or script.get_text()
                )

                if isinstance(data, dict):
                    data = [data]

                if not isinstance(data, list):
                    continue

                for item in data:

                    if not isinstance(item, dict):
                        continue

                    image = item.get("image")

                    if isinstance(image, str):

                        image = make_absolute_url(
                            image,
                            article_url
                        )

                        if valid_image_url(image):
                            return image

                    elif isinstance(image, dict):

                        image = image.get("url")

                        image = make_absolute_url(
                            image,
                            article_url
                        )

                        if valid_image_url(image):
                            return image

                    elif isinstance(image, list):

                        for img in image:

                            if not isinstance(img, str):
                                continue

                            img = make_absolute_url(
                                img,
                                article_url
                            )

                            if valid_image_url(img):
                                return img

            except Exception:
                pass

        # Otras etiquetas
        possible_names = [
            "image",
            "image_url",
            "thumbnail",
            "thumbnailUrl"
        ]

        for name in possible_names:

            meta = soup.find(
                "meta",
                attrs={"name": name}
            )

            if not meta:
                meta = soup.find(
                    "meta",
                    attrs={"property": name}
                )

            if meta and meta.get("content"):

                image = make_absolute_url(
                    meta.get("content"),
                    article_url
                )

                if valid_image_url(image):
                    return image

        # Primera imagen válida
        for img in soup.find_all("img"):

            src = (
                img.get("src")
                or img.get("data-src")
                or img.get("data-lazy-src")
            )

            image = make_absolute_url(
                src,
                article_url
            )

            if valid_image_url(image):
                return image

    except Exception as e:
        print(
            "⚠️ Error buscando imagen:",
            e
        )

    return None


def get_fallback_image(title):

    title_lower = title.lower()

    minecraft = [
        "https://images.unsplash.com/photo-1607513746994-51f730a44832?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1627856013091-fed6e4e30025?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1598550487031-0898b485212d?auto=format&fit=crop&w=1200&q=80"
    ]

    fortnite = [
        "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=1200&q=80"
    ]

    playstation = [
        "https://images.unsplash.com/photo-1606813907291-d86efa9b94db?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1592840496694-26d035b52b48?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1606144042614-b2417e99c4e3?auto=format&fit=crop&w=1200&q=80"
    ]

    xbox = [
        "https://images.unsplash.com/photo-1605901309584-818e25960a8f?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1604586376807-f73185cf586c?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1621259182978-fbf93132d53d?auto=format&fit=crop&w=1200&q=80"
    ]

    nintendo = [
        "https://images.unsplash.com/photo-1578303512597-81e6cc155b3e?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1612036782180-6f0b6cd846fe?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1580327344181-c1163234e5a0?auto=format&fit=crop&w=1200&q=80"
    ]

    pokemon = [
        "https://images.unsplash.com/photo-1613771404721-1f92d799e49f?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1612287230202-1ff1d85d1bdf?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1627856013091-fed6e4e30025?auto=format&fit=crop&w=1200&q=80"
    ]

    football = [
        "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1431324155629-1a6deb1dec8d?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1526232761682-d26e03ac148e?auto=format&fit=crop&w=1200&q=80"
    ]

    gaming = [
        "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1593305841991-05c297ba4575?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1606144042614-b2417e99c4e3?auto=format&fit=crop&w=1200&q=80"
    ]

    general = [
        "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1593305841991-05c297ba4575?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1606144042614-b2417e99c4e3?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1606813907291-d86efa9b94db?auto=format&fit=crop&w=1200&q=80"
    ]

    if "minecraft" in title_lower:
        images = minecraft

    elif "fortnite" in title_lower:
        images = fortnite

    elif "playstation" in title_lower or "ps5" in title_lower:
        images = playstation

    elif "xbox" in title_lower:
        images = xbox

    elif "nintendo" in title_lower or "switch" in title_lower:
        images = nintendo

    elif "pokemon" in title_lower or "pokémon" in title_lower:
        images = pokemon

    elif (
        "fútbol" in title_lower
        or "futbol" in title_lower
        or "fc 26" in title_lower
        or "fc 27" in title_lower
    ):
        images = football

    elif (
        "gaming" in title_lower
        or "videojuego" in title_lower
        or "videojuegos" in title_lower
        or "juego" in title_lower
        or "juegos" in title_lower
    ):
        images = gaming

    else:
        images = general

    index = sum(
        ord(char)
        for char in title
    ) % len(images)

    return images[index]


def get_news():

    print("=" * 60)
    print("Descargando noticias...")
    print("=" * 60)

    try:

        response = requests.get(
            RSS_URL,
            headers=HEADERS,
            timeout=20
        )

        response.raise_for_status()

    except Exception as e:

        print(
            "❌ Error descargando RSS:",
            e
        )

        return []

    try:

        root = ET.fromstring(
            response.content
        )

    except Exception as e:

        print(
            "❌ Error leyendo RSS:",
            e
        )

        return []

    news = []
    seen_urls = set()

    items = root.findall(".//item")

    print(
        "Noticias encontradas:",
        len(items)
    )

    for item in items:

        if len(news) >= MAX_NEWS:
            break

        title_element = item.find("title")
        link_element = item.find("link")
        date_element = item.find("pubDate")

        if title_element is None:
            continue

        if link_element is None:
            continue

        title = clean_text(
            title_element.text
        )

        google_url = clean_text(
            link_element.text
        )

        published = ""

        if date_element is not None:
            published = clean_text(
                date_element.text
            )

        if not title or not google_url:
            continue

        real_url = decode_google_news_url(
            google_url
        )

        if not real_url:
            continue

        real_url = real_url.strip()

        if real_url in seen_urls:
            continue

        seen_urls.add(real_url)

        print()
        print("📰", title)
        print("🔗", real_url)

        image = get_article_image(
            real_url
        )

        if image:

            print("✅ Imagen real encontrada")

        else:

            image = get_fallback_image(
                title
            )

            print("🖼️ Imagen de respaldo")

        news.append(
            {
                "title": title,
                "url": real_url,
                "image": image,
                "published": published
            }
        )

        time.sleep(0.3)

    return news


def main():

    news = get_news()

    print()
    print("=" * 60)

    print(
        "Noticias guardadas:",
        len(news)
    )

    print(
        "Noticias con imagen:",
        sum(
            1
            for article in news
            if article.get("image")
        )
    )

    print()

    with open(
        "news.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            news,
            file,
            ensure_ascii=False,
            indent=2
        )

    print(
        "news.json actualizado correctamente."
    )

    print("=" * 60)


if __name__ == "__main__":
    main()
