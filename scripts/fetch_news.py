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
    text = BeautifulSoup(
        text,
        "html.parser"
    ).get_text(" ")

    text = re.sub(
        r"\s+",
        " ",
        text
    )

    return text.strip()


# =========================================================
# URL DE IMAGEN
# =========================================================

def make_absolute_url(url, article_url):
    if not url:
        return None

    url = html.unescape(
        url
    ).strip()

    if url.startswith("//"):
        return "https:" + url

    if url.startswith("/"):
        parsed = urlparse(article_url)

        return (
            f"{parsed.scheme}://"
            f"{parsed.netloc}"
            f"{url}"
        )

    if (
        url.startswith("http://")
        or url.startswith("https://")
    ):
        return url

    return None


def valid_image_url(url):
    if not url:
        return False

    url_lower = url.lower()

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
        if word in url_lower:
            return False

    return (
        url_lower.startswith("http://")
        or url_lower.startswith("https://")
    )


# =========================================================
# BUSCAR IMAGEN DE LA NOTICIA
# =========================================================

def get_article_image(article_url):
    print(
        f"Buscando imagen: {article_url}"
    )

    response = download(
        article_url
    )

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
            attrs={
                "property": "og:image"
            }
        )

        if (
            og_image
            and og_image.get("content")
        ):
            image = make_absolute_url(
                og_image["content"],
                article_url
            )

            if valid_image_url(image):
                print(
                    "Imagen encontrada (og:image): "
                    f"{image}"
                )

                return image

        # -------------------------------------------------
        # 2. Twitter
        # -------------------------------------------------

        twitter_image = soup.find(
            "meta",
            attrs={
                "name": "twitter:image"
            }
        )

        if not twitter_image:
            twitter_image = soup.find(
                "meta",
                attrs={
                    "property": "twitter:image"
                }
            )

        if (
            twitter_image
            and twitter_image.get("content")
        ):
            image = make_absolute_url(
                twitter_image["content"],
                article_url
            )

            if valid_image_url(image):
                print(
                    "Imagen encontrada (Twitter): "
                    f"{image}"
                )

                return image

        # -------------------------------------------------
        # 3. JSON-LD
        # -------------------------------------------------

        scripts = soup.find_all(
            "script",
            attrs={
                "type": "application/ld+json"
            }
        )

        for script in scripts:
            try:
                data = json.loads(
                    script.string
                    or script.get_text()
                )

                objects = []

                if isinstance(data, dict):
                    objects.append(data)

                    if isinstance(
                        data.get("@graph"),
                        list
                    ):
                        objects.extend(
                            data["@graph"]
                        )

                elif isinstance(data, list):
                    objects.extend(data)

                for obj in objects:

                    if not isinstance(
                        obj,
                        dict
                    ):
                        continue

                    image_data = obj.get(
                        "image"
                    )

                    if isinstance(
                        image_data,
                        str
                    ):
                        image = make_absolute_url(
                            image_data,
                            article_url
                        )

                        if valid_image_url(
                            image
                        ):
                            print(
                                "Imagen encontrada "
                                "(JSON-LD): "
                                f"{image}"
                            )

                            return image

                    elif isinstance(
                        image_data,
                        dict
                    ):
                        image_data = (
                            image_data.get(
                                "url"
                            )
                        )

                        image = make_absolute_url(
                            image_data,
                            article_url
                        )

                        if valid_image_url(
                            image
                        ):
                            print(
                                "Imagen encontrada "
                                "(JSON-LD): "
                                f"{image}"
                            )

                            return image

                    elif isinstance(
                        image_data,
                        list
                    ):
                        for item in image_data:

                            if isinstance(
                                item,
                                str
                            ):
                                image = (
                                    make_absolute_url(
                                        item,
                                        article_url
                                    )
                                )

                                if valid_image_url(
                                    image
                                ):
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
            (
                "meta",
                "name",
                "image"
            ),
            (
                "meta",
                "property",
                "image"
            ),
            (
                "meta",
                "name",
                "thumbnail"
            ),
            (
                "meta",
                "property",
                "thumbnail"
            ),
        ]

        for tag, attribute, value in possible_tags:

            element = soup.find(
                tag,
                attrs={
                    attribute: value
                }
            )

            if (
                element
                and element.get("content")
            ):
                image = make_absolute_url(
                    element["content"],
                    article_url
                )

                if valid_image_url(image):
                    print(
                        "Imagen encontrada "
                        "(meta): "
                        f"{image}"
                    )

                    return image

        # -------------------------------------------------
        # 5. Primera imagen de la página
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
                        "Imagen encontrada "
                        "(img): "
                        f"{image}"
                    )

                    return image

    except Exception as e:
        print(
            f"Error buscando imagen: {e}"
        )

    print(
        "No se encontró imagen."
    )

    return None


# =========================================================
# IMÁGENES DE RESPALDO
# =========================================================

def get_fallback_image(title):
    """
    Devuelve diferentes imágenes de respaldo
    según el tema de la noticia.
    """

    title_lower = title.lower()

    fallback_images = {

        # MINECRAFT
        "minecraft": [
            "https://images.unsplash.com/photo-1606092195730-5d7b9af1efc5?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1627856013091-fed6e4e30025?auto=format&fit=crop&w=1200&q=80",
        ],

        # FORTNITE
        "fortnite": [
            "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=1200&q=80",
        ],

        # PLAYSTATION
        "playstation": [
            "https://images.unsplash.com/photo-1607853202273-797f1c22a38e?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1592840062661-6d2a8d8b7e5c?auto=format&fit=crop&w=1200&q=80",
        ],

        # PS5
        "ps5": [
            "https://images.unsplash.com/photo-1607853202273-797f1c22a38e?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1621259182978-fbf93132d53d?auto=format&fit=crop&w=1200&q=80",
        ],

        # XBOX
        "xbox": [
            "https://images.unsplash.com/photo-1621259182978-fbf93132d53d?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1605901309584-818e25960a8f?auto=format&fit=crop&w=1200&q=80",
        ],

        # NINTENDO
        "nintendo": [
            "https://images.unsplash.com/photo-1578303512597-81e6cc155b3e?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=1200&q=80",
        ],

        # SWITCH
        "switch": [
            "https://images.unsplash.com/photo-1578303512597-81e6cc155b3e?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1597096200317-5f8e8a9d4a9b?auto=format&fit=crop&w=1200&q=80",
        ],

        # POKEMON
        "pokemon": [
            "https://images.unsplash.com/photo-1542779283-429940ce8336?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1566576912321-d58ddd7a6088?auto=format&fit=crop&w=1200&q=80",
        ],

        # FÚTBOL
        "futbol": [
            "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1553778263-73a83bab9b0c?auto=format&fit=crop&w=1200&q=80",
        ],

        # FC
        "fc 27": [
            "https://images.unsplash.com/photo-1579952363873-27f3bade9f55?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1553778263-73a83bab9b0c?auto=format&fit=crop&w=1200&q=80",
        ],

        # GTA
        "gta": [
            "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1493711662062-fa541adb3fc8?auto=format&fit=crop&w=1200&q=80",
        ],

        # GAMING
        "gaming": [
            "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=1200&q=80",
            "https://images.unsplash.com/photo-1493711662062-fa541adb3fc8?auto=format&fit=crop&w=1200&q=80",
        ],
    }

    # -----------------------------------------------------
    # Buscar categoría por título
    # -----------------------------------------------------

    for keyword, images in fallback_images.items():

        if keyword in title_lower:

            index = (
                sum(
                    ord(character)
                    for character in title
                )
                % len(images)
            )

            image = images[index]

            print(
                "Imagen de respaldo temática "
                f"({keyword}): {image}"
            )

            return image

    # -----------------------------------------------------
    # Respaldo general
    # -----------------------------------------------------

    general_images = [
        "https://images.unsplash.com/photo-1542751371-adc38448a05e?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1511512578047-dfb367046420?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1493711662062-fa541adb3fc8?auto=format&fit=crop&w=1200&q=80",
        "https://images.unsplash.com/photo-1550745165-9bc0b252726f?auto=format&fit=crop&w=1200&q=80",
    ]

    index = (
        sum(
            ord(character)
            for character in title
        )
        % len(general_images)
    )

    image = general_images[index]

    print(
        f"Imagen de respaldo general: {image}"
    )

    return image


# =========================================================
# OBTENER NOTICIAS
# =========================================================

def get_news():

    print(
        "Descargando Google News..."
    )

    response = download(
        RSS_URL
    )

    if not response:
        return []

    try:
        root = ET.fromstring(
            response.content
        )

    except Exception as e:
        print(
            f"Error leyendo RSS: {e}"
        )

        return []

    articles = []

    for item in root.findall(".//item"):

        title_element = item.find(
            "title"
        )

        link_element = item.find(
            "link"
        )

        description_element = item.find(
            "description"
        )

        date_element = item.find(
            "pubDate"
        )

        if title_element is None:
            continue

        title = clean_text(
            title_element.text
        )

        google_link = (
            link_element.text.strip()
            if (
                link_element is not None
                and link_element.text
            )
            else ""
        )

        description = clean_text(
            description_element.text
            if description_element is not None
            else ""
        )

        date = (
            date_element.text.strip()
            if (
                date_element is not None
                and date_element.text
            )
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

    print(
        f"Noticias encontradas en RSS: "
        f"{len(articles)}"
    )

    final_news = []

    seen_urls = set()
    seen_titles = set()

    for index, article in enumerate(
        articles
    ):

        if len(final_news) >= MAX_NEWS:
            break

        title = article["title"]

        if not title:
            continue

        title_key = title.lower().strip()

        if title_key in seen_titles:
            continue

        print("")
        print(
            "=" * 60
        )

        print(
            f"Noticia "
            f"{len(final_news) + 1}: "
            f"{title}"
        )

        # -------------------------------------------------
        # Decodificar URL
        # -------------------------------------------------

        original_url = (
            decode_google_news_url(
                article["googleLink"]
            )
        )

        if not original_url:

            print(
                "No se encontró la URL original."
            )

            continue

        print(
            f"URL original: {original_url}"
        )

        # -------------------------------------------------
        # Evitar duplicados
        # -------------------------------------------------

        if original_url in seen_urls:
            continue

        seen_urls.add(
            original_url
        )

        seen_titles.add(
            title_key
        )

        # -------------------------------------------------
        # Buscar imagen real
        # -------------------------------------------------

        image = get_article_image(
            original_url
        )

        # -------------------------------------------------
        # Si no hay imagen, buscar respaldo
        # -------------------------------------------------

        if not image:

            print(
                "Usando imagen de respaldo."
            )

            image = get_fallback_image(
                title
            )

        # -------------------------------------------------
        # Guardar noticia
        # -------------------------------------------------

        news_item = {
            "title": title,
            "description": article[
                "description"
            ],
            "link": original_url,
            "googleLink": article[
                "googleLink"
            ],
            "image": image,
            "category": "Para ti",
            "game": "",
            "date": article["date"]
        }

        final_news.append(
            news_item
        )

        # -------------------------------------------------
        # Pequeña pausa
        # -------------------------------------------------

        time.sleep(0.3)

    # =====================================================
    # GUARDAR NEWS.JSON
    # =====================================================

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
    print(
        "=" * 60
    )

    print(
        f"Noticias guardadas: "
        f"{len(final_news)}"
    )

    print(
        f"Noticias con imagen: "
        f"{images}"
    )

    print(
        "news.json actualizado correctamente."
    )

    print(
        "=" * 60
    )


# =========================================================
# INICIO
# =========================================================

if __name__ == "__main__":
    main()
