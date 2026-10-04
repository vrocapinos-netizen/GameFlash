import json
import re
import time
import html
import requests
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse


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


def download(url, timeout=15):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=timeout,
            allow_redirects=True
        )

        if response.status_code != 200:
            print("❌ Error HTTP", response.status_code, url)
            return None

        return response.text

    except Exception as e:
        print("❌ Error descargando:", url, e)
        return None


def get_decoding_params():
    """
    Obtiene los parámetros necesarios para descodificar
    los enlaces de Google News.
    """

    url = "https://news.google.com/"

    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15
        )

        text = response.text

        match = re.search(
            r'window\.WIZ_global_data\s*=\s*(\{.*?\});',
            text
        )

        if not match:
            return None

        data = json.loads(match.group(1))

        return data

    except Exception:
        return None


def decode_google_news_url(url):
    """
    Intenta convertir una URL de Google News
    en la URL real del artículo.
    """

    if not url:
        return None

    if not url.startswith("https://news.google.com"):
        return url

    try:
        parsed = urlparse(url)

        if not parsed.path.startswith("/rss/articles/"):
            return url

        article_id = parsed.path.split("/rss/articles/")[-1]

        article_id = article_id.strip("/")

        # Método actual de Google News
        batchexecute_url = (
            "https://news.google.com/_/DotsSplashUi/data/batchexecute"
        )

        payload = [
            [
                "Fbv4je",
                json.dumps(
                    [
                        [
                            article_id
                        ]
                    ]
                ),
                None,
                "generic"
            ]
        ]

        response = requests.post(
            batchexecute_url,
            headers={
                **HEADERS,
                "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8"
            },
            data={
                "f.req": json.dumps(payload)
            },
            timeout=15
        )

        if response.status_code != 200:
            return url

        text = response.text

        urls = re.findall(
            r'https?://[^"\\\s]+',
            text
        )

        for possible_url in urls:
            possible_url = html.unescape(possible_url)

            possible_url = possible_url.replace("\\/", "/")

            if (
                "news.google.com" not in possible_url
                and not possible_url.startswith("https://www.google.com")
            ):
                return possible_url

        # Segundo método
        encoded = quote(url, safe="")

        decoder_url = (
            "https://news.google.com/rss/articles/"
            + article_id
        )

        response = requests.get(
            decoder_url,
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
        print("⚠️ No se pudo descodificar:", e)

    return url


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

    bad_extensions = (
        ".svg",
        ".ico"
    )

    if url.endswith(bad_extensions):
        return False

    return (
        url.startswith("http://")
        or url.startswith("https://")
    )


def get_article_image(article_url):
    """
    Busca una imagen REAL del artículo.
    No utiliza imágenes de respaldo.
    """

    try:
        response = requests.get(
            article_url,
            headers=HEADERS,
            timeout=15,
            allow_redirects=True
        )

        if response.status_code != 200:
            print(
                "⚠️ No se pudo acceder al artículo:",
                response.status_code,
                article_url
            )
            return None

        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # 1. Open Graph
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

        # 2. Twitter
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

        # 3. Twitter image src
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

        # 4. JSON-LD
        scripts = soup.find_all(
            "script",
            type="application/ld+json"
        )

        for script in scripts:

            try:
                data = json.loads(
                    script.string or script.get_text()
                )

                items = data

                if isinstance(data, dict):
                    items = [data]

                if not isinstance(items, list):
                    continue

                for item in items:

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

                    if isinstance(image, list):

                        for img in image:

                            if not isinstance(img, str):
                                continue

                            img = make_absolute_url(
                                img,
                                article_url
                            )

                            if valid_image_url(img):
                                return img

                    if isinstance(image, dict):

                        image_url = image.get("url")

                        image_url = make_absolute_url(
                            image_url,
                            article_url
                        )

                        if valid_image_url(image_url):
                            return image_url

            except Exception:
                pass

        # 5. Otras etiquetas meta
        possible_meta = [
            "image",
            "image_url",
            "thumbnail",
            "thumbnailUrl",
            "og:image:url",
            "og:image:secure_url"
        ]

        for name in possible_meta:

            meta = soup.find(
                "meta",
                attrs={
                    "name": name
                }
            )

            if not meta:

                meta = soup.find(
                    "meta",
                    attrs={
                        "property": name
                    }
                )

            if meta and meta.get("content"):

                image = make_absolute_url(
                    meta.get("content"),
                    article_url
                )

                if valid_image_url(image):
                    return image

        # 6. Primera imagen grande encontrada
        images = soup.find_all("img")

        for img in images:

            src = (
                img.get("src")
                or img.get("data-src")
                or img.get("data-lazy-src")
            )

            image = make_absolute_url(
                src,
                article_url
            )

            if not valid_image_url(image):
                continue

            width = img.get("width")

            height = img.get("height")

            try:
                if width and int(width) < 200:
                    continue

                if height and int(height) < 150:
                    continue

            except Exception:
                pass

            return image

    except Exception as e:

        print(
            "⚠️ Error buscando imagen:",
            e
        )

    return None


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

    items = root.findall(
        ".//item"
    )

    print(
        "Noticias encontradas en RSS:",
        len(items)
    )

    for item in items:

        if len(news) >= MAX_NEWS:
            break

        title_element = item.find("title")

        link_element = item.find("link")

        pub_date_element = item.find("pubDate")

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

        pub_date = ""

        if pub_date_element is not None:
            pub_date = clean_text(
                pub_date_element.text
            )

        if not title or not google_url:
            continue

        # Descodificar Google News
        real_url = decode_google_news_url(
            google_url
        )

        if not real_url:
            continue

        # Limpiar posibles restos
        real_url = real_url.strip()

        if real_url.startswith("["):
            match = re.search(
                r"\((https?://[^)]+)\)",
                real_url
            )

            if match:
                real_url = match.group(1)

        real_url = real_url.rstrip(":")

        if real_url in seen_urls:
            continue

        seen_urls.add(real_url)

        print()
        print("📰", title)
        print("🔗", real_url)

        # Buscar imagen REAL
        image = get_article_image(
            real_url
        )

        # Si no hay imagen, NO PUBLICAR
        if not image:

            print(
                "❌ Sin imagen → noticia descartada"
            )

            continue

        print(
            "✅ Imagen encontrada"
        )

        news.append(
            {
                "title": title,
                "url": real_url,
                "image": image,
                "published": pub_date
            }
        )

        time.sleep(0.3)

    return news


def main():

    news = get_news()

    print()
    print("=" * 60)

    print(
        "Noticias publicadas:",
        len(news)
    )

    print(
        "Noticias descartadas sin imagen:",
        MAX_NEWS - len(news)
        if len(news) < MAX_NEWS
        else 0
    )

    print("=" * 60)

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

    print()
    print(
        "news.json actualizado correctamente."
    )

    print("=" * 60)


if __name__ == "__main__":
    main()
