"""
Módulo de extracción y Modo Lectura (In-App Reader) para Polaris.
Permite leer artículos directamente en la app limpios de publicidad, scripts y rastreadores.
Detecta si un artículo requiere suscripción oficial para informar transparentemente al usuario.
"""

import urllib.request
import json
import re
import html
from typing import Dict, Any, List
from bs4 import BeautifulSoup

BROWSER_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
    'Accept-Language': 'es-ES,es;q=0.9,en;q=0.8',
    'Sec-Fetch-Site': 'none',
    'Sec-Fetch-Mode': 'navigate',
    'Sec-Fetch-User': '?1',
    'Sec-Fetch-Dest': 'document',
    'Cache-Control': 'max-age=0'
}

# Palabras o frases que suelen ser bloques de publicidad, cookies o newsletters
NOISE_PATTERNS = [
    r'newsletter', r'suscr[ií]bete', r'todos los derechos reservados',
    r'pol[ií]tica de privacidad', r'aviso legal', r'configuraci[oó]n de cookies',
    r'descarga la app', r's[ií]guenos en', r'le puede interesar',
    r'noticias relacionadas', r'apúntate gratis', r'comentarios'
]

def clean_text(text: str) -> str:
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def extract_article(url: str, source_hint: str = "") -> Dict[str, Any]:
    """
    Descarga el contenido de un artículo y extrae el texto limpio, titular,
    imágenes y metadatos de acceso (gratuito vs suscriptor).
    """
    try:
        req = urllib.request.Request(url, headers=BROWSER_HEADERS)
        with urllib.request.urlopen(req, timeout=9) as response:
            raw_html = response.read().decode('utf-8', errors='ignore')

        soup = BeautifulSoup(raw_html, 'html.parser')

        # Eliminar scripts, estilos, iframes, nav, footer, banners
        for tag in soup(['script', 'style', 'iframe', 'nav', 'footer', 'header', 'aside', 'noscript', 'svg']):
            tag.decompose()

        # 1. Detectar si el artículo está marcado como de pago / suscripción
        is_paywalled = False
        paywall_selectors = [
            '.paywall', '.ue-c-article__premium', '.c-detail__premium',
            '.c-gate', '.fc-dialog-container', '[data-paywall]',
            '.ep-article__premium'
        ]
        for sel in paywall_selectors:
            if soup.select(sel):
                is_paywalled = True
                break

        # Comprobar JSON-LD (Schema.org isAccessibleForFree)
        for tag in soup.find_all('script', type='application/ld+json'):
            try:
                data = json.loads(tag.string)
                items = data if isinstance(data, list) else [data]
                for item in items:
                    if isinstance(item, dict):
                        if item.get('isAccessibleForFree') is False:
                            is_paywalled = True
                        has_part = item.get('hasPart')
                        if isinstance(has_part, dict) and has_part.get('isAccessibleForFree') is False:
                            is_paywalled = True
            except Exception:
                pass

        # 2. Extraer titular principal
        title = ""
        h1 = soup.find('h1')
        if h1:
            title = clean_text(h1.get_text())
        if not title:
            og_title = soup.find('meta', property='og:title')
            if og_title and og_title.get('content'):
                title = clean_text(og_title['content'])

        # 3. Extraer entradilla / subtítulo
        lead = ""
        lead_el = soup.find(class_=re.compile(r'lead|subheading|ep-article__lead|ue-c-article__standfirst', re.I))
        if lead_el:
            lead = clean_text(lead_el.get_text())
        if not lead:
            desc_tag = soup.find('meta', property='og:description') or soup.find('meta', attrs={'name': 'description'})
            if desc_tag and desc_tag.get('content'):
                lead = clean_text(desc_tag['content'])

        # 4. Extraer autor y fecha
        author = ""
        author_el = soup.find(class_=re.compile(r'author|byline|ue-c-article__byline', re.I))
        if author_el:
            author = clean_text(author_el.get_text())
        if not author:
            meta_author = soup.find('meta', attrs={'name': 'author'})
            if meta_author and meta_author.get('content'):
                author = clean_text(meta_author['content'])

        # 5. Extraer imagen principal y pie
        image_url = None
        image_caption = None
        og_image = soup.find('meta', property='og:image')
        if og_image and og_image.get('content'):
            image_url = og_image['content']

        fig = soup.find('figure')
        if fig:
            img_tag = fig.find('img')
            if img_tag and not image_url:
                image_url = img_tag.get('src') or img_tag.get('data-src')
            caption_tag = fig.find('figcaption')
            if caption_tag:
                image_caption = clean_text(caption_tag.get_text())

        # 6. Extraer cuerpo de párrafos
        paragraphs = []
        body_container = soup.find('article') or soup.find('div', class_=re.compile(r'article__body|article_body|story-body|ue-c-article__body|c-detail__body', re.I))
        
        target_soup = body_container if body_container else soup

        for p in target_soup.find_all('p'):
            txt = clean_text(p.get_text())
            # Filtrar párrafos demasiado breves o ruidosos
            if len(txt) < 35:
                continue
            
            is_noise = False
            for pat in NOISE_PATTERNS:
                if re.search(pat, txt, re.I):
                    is_noise = True
                    break
            
            if not is_noise:
                paragraphs.append(txt)

        # Si no encontramos párrafos en article, usar los encontrados generales
        if not paragraphs:
            for p in soup.find_all('p'):
                txt = clean_text(p.get_text())
                if len(txt) > 45:
                    paragraphs.append(txt)

        # Contar palabras y tiempo de lectura
        full_text = " ".join(paragraphs)
        word_count = len(full_text.split())
        reading_time_min = max(1, round(word_count / 190))

        return {
            "status": "success",
            "url": url,
            "title": title,
            "lead": lead,
            "author": author,
            "image_url": image_url,
            "image_caption": image_caption,
            "paragraphs": paragraphs,
            "word_count": word_count,
            "reading_time_min": reading_time_min,
            "is_paywalled": is_paywalled
        }

    except Exception as e:
        return {
            "status": "error",
            "url": url,
            "message": f"No se pudo cargar el artículo directamente: {str(e)}",
            "paragraphs": [],
            "is_paywalled": False
        }
