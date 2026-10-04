import json
import re
import time
import html
import requests
import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup
from urllib.parse import quote, urlparse


# =========================================================
# CONFIGURACIÓN
# =========================================================

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
    "Accept": (
        "text/html,application/xhtml+xml,"
        "application/xml;q=0.9,image/webp,*/*;q=0.8"
    ),
}


# =========================================================
# DESCARGAR
# =========================================================

def download(url, timeout=15):
    try:
        response = requests.get(
            url,
            headers=HEADERS,
            timeout=timeout,
            allow_redirects=True
        )

        response.raise_for_status()
        return response

    except Exception as e:
        print(f"Error descargando {url}: {e}")
        return None


# =========================================================
# DECODIFICAR GOOGLE NEWS
# =========================================================

def get_decoding_params(gn_art_id):
    try:
        url = f"https://news.google.com/rss/articles/{gn_art_id}"

        response = requests.get(
            url,
            headers=HEADERS,
            timeout=15
        )

        response.raise_for_status()

        soup = BeautifulSoup(response.text, "html.parser")

        div = soup.select_one("c-wiz > div")

        if not div:
            return None

        signature = div.get("data-n-a-sg")
        timestamp = div.get("data-n-a-ts")

        if not signature or not timestamp:
            return None

        return {
            "signature": signature,
            "timestamp": timestamp,
            "gn_art_id": gn_art_id
        }

    except Exception as e:
        print(f"No se pudieron obtener parámetros: {e}")
        return None


def decode_google_news_url(source_url):
    try:
        path = urlparse(source_url).path
        gn_art_id = path.rstrip("/").split("/")[-1]

        if not gn_art_id:
            return None

        params = get_decoding_params(gn_art_id)

        if not params:
            return None

        articles_req = [
            "Fbv4je",
            (
                '["garturlreq",'
                '[["X","X",["X","X"],null,null,1,1,"US:en",null,1,'
                'null,null,null,null,null,0,1],'
                '"X","X",1,[1,1,1],1,1,null,0,0,null,0],'
                f'"{params["gn_art_id"]}",'
                f'{params["timestamp"]},'
                f'"{params["signature"]}"]'
            )
        ]

        payload = "f.req=" + quote(
            json.dumps([[articles_req]])
        )

        response = requests.post(
            "https://news.google.com/_/DotsSplashUi/data/batchexecute",
            headers={
                **HEADERS,
                "Content-Type":
                    "application/x-www-form-urlencoded;charset=UTF-8"
            },
            data=payload,
            timeout=20
        )

        response.raise_for_status()

        parts = response.text.split("\n\n")

        if len(parts) < 2:
            return None

        data = json.loads(parts[1])

        for item in data:
            try:
                if len(item) > 2:
                    result = json.loads(item[2])

                    if isinstance(result, list) and len(result) > 1:
                        decoded_url = result[1]

                        if (
                            isinstance(decoded_url, str)
                            and decoded_url.startswith("http")
                        ):
                            # Limpiar posibles caracteres que Google
                            # pueda dejar al final de la URL.
                            decoded_url = re.sub(
                                r'[)"\']+$',
                                '',
                                decoded_url
                            )

                            return decoded_url

            except Exception:
                continue

    except Exception as e:
        print(f"Error decodificando Google News: {e}")

    return None


# =========================================================
# LIMPIAR TEXTO
# =========================================================

def clean_text(text):
    if not text:
        return ""

    text = html.unescape(text)
    text = BeautifulSoup(text, "html.parser").get_text(" ")

    text = re.sub(r"\s+", " ", text)

    return text.strip()


# =========================================================
# BUSCAR IMAGEN
# =========================================================

def make_absolute_url(url, article_url):
    if not url:
        return None

    url = html.unescape(url).strip()

    if url.startswith("//"):
        return "https:" + url

    if url.startswith("/"):
        parsed = urlparse(article_url)

        return (
            f"{parsed.scheme}://{parsed.netloc}{url}"
        )

    if url.startswith("http://") or url.startswith("https://"):
        return url

    return None


def valid_image_url(url):
    if not url:
        return False

    url = url.lower()

    bad_words = [
        "logo",
        "avatar",
        "favicon",
        "icon",
        "sprite",
        "tracking",
        "analytics",
        "pixel",
        "placeholder",
        "blank.gif",
        "1x1"
    ]

    for word in bad_words:
        if word in url:
            return False

    return (
        url.startswith("http://")
        or url.startswith("https://")
    )


def get_article_image(article_url):
    print(f"Buscando imagen: {article_url}")

    response = download(article_url)

    if not response:
        return None

    try:
        soup = BeautifulSoup(
            response.text,
            "html.parser"
        )

        # -------------------------------------------------
        # 1. Open Graph
        # -------------------------------------------------

        og_image = soup.find(
            "meta",
            attrs={"property": "og:image"}
        )

        if og_image and og_image.get("content"):
            image = make_absolute_url(
                og_image["content"],
                article_url
            )

            if valid_image_url(image):
                print(f"Imagen encontrada (og:image): {image}")
                return image

        # -------------------------------------------------
        # 2. Twitter
        # -------------------------------------------------

        twitter_image = soup.find(
            "meta",
            attrs={"name": "twitter:image"}
        )

        if not twitter_image:
            twitter_image = soup.find(
                "meta",
                attrs={"property": "twitter:image"}
            )

        if twitter_image and twitter_image.get("content"):
            image = make_absolute_url(
                twitter_image["content"],
                article_url
            )

            if valid_image_url(image):
                print(
                    f"Imagen encontrada (Twitter): {image}"
                )
                return image

        # -------------------------------------------------
        # 3. JSON-LD
        # -------------------------------------------------

        scripts = soup.find_all(
            "script",
            attrs={"type": "application/ld+json"}
        )

        for script in scripts:
            try:
                data = json.loads(
                    script.string or script.get_text()
                )

                objects = []

                if isinstance(data, dict):
                    objects.append(data)

                    if isinstance(data.get("@graph"), list):
                        objects.extend(data["@graph"])

                elif isinstance(data, list):
                    objects.extend(data)

                for obj in objects:
                    if not isinstance(obj, dict):
                        continue

                    image_data = obj.get("image")

                    if isinstance(image_data, str):
                        image = make_absolute_url(
                            image_data,
                            article_url
                        )

                        if valid_image_url(image):
                            print(
                                f"Imagen encontrada (JSON-LD): {image}"
                            )
                            return image

                    elif isinstance(image_data, dict):
                        image_data = image_data.get("url")

                        image = make_absolute_url(
                            image_data,
                            article_url
                        )

                        if valid_image_url(image):
                            print(
                                f"Imagen encontrada (JSON-LD): {image}"
                            )
                            return image

                    elif isinstance(image_data, list):
                        for item in image_data:
                            if isinstance(item, str):
                                image = make_absolute_url(
                                    item,
                                    article_url
                                )

                                if valid_image_url(image):
                                    print(
                                        "Imagen encontrada "
                                        "(JSON-LD lista)"
                                    )
                                    return image

            except Exception:
                continue

        # -------------------------------------------------
        # 4. Meta tags alternativos
        # -------------------------------------------------

        possible_tags = [
            ("meta", "name", "image"),
            ("meta", "property", "image"),
            ("meta", "name", "thumbnail"),
            ("meta", "property", "thumbnail"),
        ]

        for tag, attribute, value in possible_tags:
            element = soup.find(
                tag,
                attrs={attribute: value}
            )

            if element and element.get("content"):
                image = make_absolute_url(
                    element["content"],
                    article_url
                )

                if valid_image_url(image):
                    print(
                        f"Imagen encontrada (meta): {image}"
                    )
                    return image

        # -------------------------------------------------
        # 5. Primera imagen grande de la página
        # -------------------------------------------------

        for img in soup.find_all("img"):
            candidates = [
                img.get("src"),
                img.get("data-src"),
                img.get("data-lazy-src"),
                img.get("data-original"),
            ]

            for candidate in candidates:
                image = make_absolute_url(
                    candidate,
                    article_url
                )

                if valid_image_url(image):
                    print(
                        f"Imagen encontrada (img): {image}"
                    )
                    return image

    except Exception as e:
        print(f"Error buscando imagen: {e}")

    print("No se encontró imagen.")
    return None


# =========================================================
# IMAGEN DE RESPALDO
# =========================================================

def get_fallback_image(title):
    """
    Busca una imagen relacionada con la noticia
    usando Wikimedia Commons.
    """

    try:
        # Quitamos palabras poco útiles para mejorar la búsqueda
        stop_words = {
            "el", "la", "los", "las", "un", "una",
            "de", "del", "en", "con", "para", "por",
            "y", "o", "que", "ya", "es", "más",
            "a", "se", "su", "al"
        }

        words = re.findall(
            r"[A-Za-zÀ-ÿ0-9]+",
            title.lower()
        )

        useful_words = [
            word
            for word in words
            if word not in stop_words and len(word) > 2
        ]

        search_text = " ".join(
            useful_words[:8]
        )

        # Añadimos gaming para ayudar a encontrar
        # imágenes relacionadas con videojuegos.
        search_text += " video game"

        api_url = "https://commons.wikimedia.org/w/api.php"

        params = {
            "action": "query",
            "generator": "search",
            "gsrsearch": search_text,
            "gsrnamespace": 6,
            "gsrlimit": 5,
            "prop": "imageinfo",
            "iiprop": "url",
            "iiurlwidth": 1200,
            "format": "json"
        }

        response = requests.get(
            api_url,
            params=params,
            headers=HEADERS,
            timeout=15
        )

        response.raise_for_status()

        data = response.json()

        pages = data.get(
            "query",
            {}
        ).get(
            "pages",
            {}
        )

        for page in pages.values():

            imageinfo = page.get(
                "imageinfo"
            )

            if not imageinfo:
                continue

            image = imageinfo[0].get(
                "thumburl"
            )

            if not image:
                image = imageinfo[0].get(
                    "url"
                )

            if valid_image_url(image):
                print(
                    f"Imagen relacionada encontrada: {image}"
                )

                return image

    except Exception as e:
        print(
            f"No se pudo encontrar imagen relacionada: {e}"
        )

    # Último respaldo
    print(
        "No se encontró imagen relacionada. "
        "Usando imagen genérica."
    )

    return (
        "https://images.unsplash.com/"
        "photo-1542751371-adc38448a05e"
        "?auto=format&fit=crop&w=1200&q=80"
    )
# =========================================================
# OBTENER NOTICIAS
# =========================================================

def get_news():
    print("Descargando Google News...")

    response = download(RSS_URL)

    if not response:
        return []

    try:
        root = ET.fromstring(response.content)

    except Exception as e:
        print(f"Error leyendo RSS: {e}")
        return []

    articles = []

    for item in root.findall(".//item"):
        title_element = item.find("title")
        link_element = item.find("link")
        description_element = item.find("description")
        date_element = item.find("pubDate")

        if title_element is None:
            continue

        title = clean_text(
            title_element.text
        )

        google_link = (
            link_element.text.strip()
            if link_element is not None
            and link_element.text
            else ""
        )

        description = clean_text(
            description_element.text
            if description_element is not None
            else ""
        )

        date = (
            date_element.text.strip()
            if date_element is not None
            and date_element.text
            else ""
        )

        if not google_link:
            continue

        articles.append({
            "title": title,
            "description": description,
            "googleLink": google_link,
            "date": date
        })

    return articles


# =========================================================
# PROGRAMA PRINCIPAL
# =========================================================

def main():

    articles = get_news()

    print(f"Noticias encontradas en RSS: {len(articles)}")

    final_news = []
    seen_urls = set()
    seen_titles = set()

    for index, article in enumerate(articles):

        if len(final_news) >= MAX_NEWS:
            break

        title = article["title"]

        if not title:
            continue

        title_key = title.lower().strip()

        if title_key in seen_titles:
            continue

        print("")
        print("=" * 60)
        print(
            f"Noticia {len(final_news) + 1}: {title}"
        )

        # -------------------------------------------------
        # Decodificar URL
        # -------------------------------------------------

        original_url = decode_google_news_url(
            article["googleLink"]
        )

        if not original_url:
            print("No se encontró la URL original.")
            continue

        print(f"URL original: {original_url}")

        # -------------------------------------------------
        # Evitar duplicados
        # -------------------------------------------------

        if original_url in seen_urls:
            continue

        seen_urls.add(original_url)
        seen_titles.add(title_key)

        # -------------------------------------------------
        # Buscar imagen
        # -------------------------------------------------

        image = get_article_image(
            original_url
        )

        # -------------------------------------------------
        # FALLBACK
        # -------------------------------------------------

        if not image:
            print(
                "Usando imagen de respaldo."
            )

            image = get_fallback_image(title)

        # -------------------------------------------------
        # Guardar noticia
        # -------------------------------------------------

        news_item = {
            "title": title,
            "description": article["description"],
            "link": original_url,
            "googleLink": article["googleLink"],
            "image": image,
            "category": "Para ti",
            "game": "",
            "date": article["date"]
        }

        final_news.append(news_item)

        # Pequeña pausa para no bombardear las webs
        time.sleep(0.3)

    # -----------------------------------------------------
    # Guardar JSON
    # -----------------------------------------------------

    with open(
        "news.json",
        "w",
        encoding="utf-8"
    ) as file:

        json.dump(
            final_news,
            file,
            ensure_ascii=False,
            indent=2
        )

    images = sum(
        1
        for article in final_news
        if article.get("image")
    )

    print("")
    print("=" * 60)
    print(f"Noticias guardadas: {len(final_news)}")
    print(f"Noticias con imagen: {images}")
    print("news.json actualizado correctamente.")
    print("=" * 60)


if __name__ == "__main__":
    main()
