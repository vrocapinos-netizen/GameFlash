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
    try:
        url = "https://news.google.com/"

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

        return json.loads(match.group(1))

    except Exception:
        return None


def decode_google_news_url(url):
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

        batchexecute_url = (
            "https://news.google.com/_/DotsSplashUi/data/batchexecute"
        )

        payload = [
            [
                "Fbv4je",
                json.dumps([[article_id]]),
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

            possible_url = html.unescape(
                possible_url
            )

            possible_url = possible_url.replace(
                "\\/",
                "/"
            )

            if (
                "news.google.com" not in possible_url
                and not possible_url.startswith(
                    "https://www.google.com"
                )
            ):
                return possible_url

        response = requests.get(
            "https://news.google.com/rss/articles/" + article_id,
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
        print(
            "⚠️ No se pudo descodificar:",
            e
        )

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
        return "
