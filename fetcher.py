"""
Módulo de recolección y normalización de noticias en tiempo real.
Descarga y procesa en paralelo los feeds RSS/Atom de:
- El País
- El Mundo
- El Confidencial
- ABC
"""

import time
import html
import re
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Any, Optional

from analyzer import analyzer, NEWSPAPER_PROFILES

FEEDS_CONFIG = [
    # El País (Feed maestro consolidado con Portada, España, Internacional, Economía, Opinión)
    {
        "source": "El País",
        "category": "Portada",
        "url": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/portada",
        "type": "rss"
    },

    # El Mundo
    {
        "source": "El Mundo",
        "category": "Portada",
        "url": "https://e00-elmundo.uecdn.es/elmundo/rss/portada.xml",
        "type": "rss"
    },
    {
        "source": "El Mundo",
        "category": "España",
        "url": "https://e00-elmundo.uecdn.es/elmundo/rss/espana.xml",
        "type": "rss"
    },
    {
        "source": "El Mundo",
        "category": "Economía",
        "url": "https://e00-elmundo.uecdn.es/elmundo/rss/economia.xml",
        "type": "rss"
    },

    # El Confidencial
    {
        "source": "El Confidencial",
        "category": "España",
        "url": "https://rss.elconfidencial.com/espana/",
        "type": "atom"
    },
    {
        "source": "El Confidencial",
        "category": "Mundo",
        "url": "https://rss.elconfidencial.com/mundo/",
        "type": "atom"
    },
    {
        "source": "El Confidencial",
        "category": "Economía",
        "url": "https://rss.elconfidencial.com/economia/",
        "type": "atom"
    },

    # ABC
    {
        "source": "ABC",
        "category": "Portada",
        "url": "https://www.abc.es/rss/2.0/portada/",
        "type": "rss"
    },
    {
        "source": "ABC",
        "category": "España",
        "url": "https://www.abc.es/rss/2.0/espana/",
        "type": "rss"
    },
    {
        "source": "ABC",
        "category": "Economía",
        "url": "https://www.abc.es/rss/2.0/economia/",
        "type": "rss"
    }
]

def clean_html(text: str) -> str:
    """Elimina etiquetas HTML, normaliza entidades y espacios."""
    if not text:
        return ""
    text = html.unescape(text)
    text = re.sub(r'<[^>]+>', ' ', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def parse_datetime(date_str: str) -> datetime:
    """Parsea fechas RFC 822 o ISO 8601 a datetime aware."""
    if not date_str:
        return datetime.now(timezone.utc)
    try:
        dt = parsedate_to_datetime(date_str)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        try:
            clean = date_str.replace('Z', '+00:00')
            dt = datetime.fromisoformat(clean)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            return dt
        except Exception:
            return datetime.now(timezone.utc)

def format_relative_time(dt: datetime) -> str:
    """Devuelve una cadena legible en español del tiempo transcurrido."""
    now = datetime.now(timezone.utc)
    diff = now - dt
    seconds = max(0, int(diff.total_seconds()))
    minutes = seconds // 60
    hours = minutes // 60
    days = hours // 24

    if minutes < 2:
        return "hace un instante"
    elif minutes < 60:
        return f"hace {minutes} min"
    elif hours < 24:
        return f"hace {hours} h"
    elif days == 1:
        return "ayer"
    elif days < 7:
        return f"hace {days} días"
    else:
        return dt.strftime("%d/%m/%Y")

class NewsFetcher:
    def __init__(self, cache_ttl_seconds: int = 420):
        self.cache_ttl = cache_ttl_seconds
        self._cached_articles: List[Dict[str, Any]] = []
        self._last_fetch_time: float = 0
        self._fetch_in_progress = False

    def fetch_feed(self, config: Dict[str, str]) -> List[Dict[str, Any]]:
        """Descarga y procesa un feed individual."""
        source = config["source"]
        feed_type = config["type"]
        default_cat = config.get("category", "General")
        url = config["url"]
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "application/rss+xml, application/atom+xml, text/xml, application/xml"
        }
        
        articles = []
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=8) as response:
                content = response.read()
            
            root = ET.fromstring(content)
            
            if feed_type == "rss":
                # Namespaces comunes en RSS
                items = root.findall(".//item")
                for it in items:
                    title = clean_html(it.findtext("title", ""))
                    link = clean_html(it.findtext("link", ""))
                    if not title or not link:
                        continue
                    
                    description = clean_html(it.findtext("description", ""))
                    pub_date_str = it.findtext("pubDate", "")
                    pub_dt = parse_datetime(pub_date_str)
                    
                    # Autor
                    author = clean_html(it.findtext("dc:creator", "", {"dc": "http://purl.org/dc/elements/1.1/"}))
                    if not author:
                        author = clean_html(it.findtext("author", ""))
                    if not author:
                        author = source

                    # Extracción de imagen
                    image_url = None
                    enc = it.find("enclosure")
                    if enc is not None and "image" in enc.attrib.get("type", ""):
                        image_url = enc.attrib.get("url")
                    
                    if not image_url:
                        media_content = it.find("{http://search.yahoo.com/mrss/}content")
                        if media_content is not None:
                            image_url = media_content.attrib.get("url")
                    
                    if not image_url:
                        media_thumb = it.find("{http://search.yahoo.com/mrss/}thumbnail")
                        if media_thumb is not None:
                            image_url = media_thumb.attrib.get("url")
                    
                    # Intentar buscar img en descripción
                    if not image_url:
                        raw_desc = it.findtext("description", "") or ""
                        img_match = re.search(r'<img[^>]+src=["\']([^"\']+)["\']', raw_desc)
                        if img_match:
                            image_url = img_match.group(1)

                    category = clean_html(it.findtext("category", "")) or default_cat

                    articles.append({
                        "id": f"{source}_{abs(hash(link))}",
                        "source": source,
                        "title": title,
                        "description": description,
                        "link": link,
                        "published_at": pub_dt.isoformat(),
                        "published_timestamp": pub_dt.timestamp(),
                        "relative_time": format_relative_time(pub_dt),
                        "author": author,
                        "category": category,
                        "image_url": image_url
                    })
            else:
                # Atom Feed (El Confidencial)
                ns = {
                    "atom": "http://www.w3.org/2005/Atom",
                    "media": "https://search.yahoo.com/mrss/"
                }
                entries = root.findall("atom:entry", ns)
                for entry in entries:
                    title = clean_html(entry.findtext("atom:title", "", ns))
                    link_el = entry.find("atom:link", ns)
                    link = link_el.attrib.get("href", "") if link_el is not None else ""
                    if not title or not link:
                        continue
                    
                    description = clean_html(entry.findtext("atom:summary", "", ns))
                    updated_str = entry.findtext("atom:updated", "", ns) or entry.findtext("atom:published", "", ns)
                    pub_dt = parse_datetime(updated_str)

                    author_el = entry.find("atom:author/atom:name", ns)
                    author = clean_html(author_el.text) if author_el is not None and author_el.text else source

                    # Imagen
                    image_url = None
                    media_content = entry.find("media:content", ns)
                    if media_content is not None:
                        image_url = media_content.attrib.get("url")
                    if not image_url:
                        media_thumb = entry.find("media:thumbnail", ns)
                        if media_thumb is not None:
                            image_url = media_thumb.attrib.get("url")

                    category_el = entry.find("atom:category", ns)
                    category = category_el.attrib.get("term", default_cat) if category_el is not None else default_cat

                    articles.append({
                        "id": f"{source}_{abs(hash(link))}",
                        "source": source,
                        "title": title,
                        "description": description,
                        "link": link,
                        "published_at": pub_dt.isoformat(),
                        "published_timestamp": pub_dt.timestamp(),
                        "relative_time": format_relative_time(pub_dt),
                        "author": author,
                        "category": category,
                        "image_url": image_url
                    })

        except Exception as e:
            print(f"[NewsFetcher] Error al descargar {source} ({url}): {e}")
        
        return articles

    def get_articles(self, force_refresh: bool = False) -> List[Dict[str, Any]]:
        """Devuelve la lista unificada y analizada de noticias con caché."""
        now = time.time()
        if not force_refresh and self._cached_articles and (now - self._last_fetch_time < self.cache_ttl):
            return self._cached_articles

        all_raw_articles = []
        with ThreadPoolExecutor(max_workers=8) as executor:
            future_to_feed = {executor.submit(self.fetch_feed, cfg): cfg for cfg in FEEDS_CONFIG}
            for future in as_completed(future_to_feed):
                try:
                    res = future.result()
                    all_raw_articles.extend(res)
                except Exception as e:
                    print(f"[NewsFetcher] Worker error: {e}")

        # Deduplicar por enlace o título similar dentro del mismo medio
        unique_articles = {}
        for art in all_raw_articles:
            # Clave única
            norm_key = (art["source"], art["link"].split('?')[0])
            if norm_key not in unique_articles:
                unique_articles[norm_key] = art

        processed_articles = list(unique_articles.values())

        # Ejecutar análisis de polarización en cada noticia
        for art in processed_articles:
            analysis = analyzer.analyze(art["title"], art["description"], art["source"])
            art["polarization"] = analysis

        # Ordenar por fecha de publicación descendente (más recientes primero)
        processed_articles.sort(key=lambda x: x["published_timestamp"], reverse=True)

        self._cached_articles = processed_articles
        self._last_fetch_time = now
        print(f"[NewsFetcher] Actualizados {len(processed_articles)} artículos en caché.")
        return self._cached_articles

    def get_stats(self) -> Dict[str, Any]:
        """Calcula estadísticas globales de polarización agregadas por periódico."""
        articles = self.get_articles()
        by_source = {k: [] for k in NEWSPAPER_PROFILES.keys()}
        
        all_markers_freq = {}

        for art in articles:
            src = art["source"]
            if src in by_source:
                by_source[src].append(art)
            
            for m in art["polarization"]["detected_markers"]:
                term = m["term"]
                all_markers_freq[term] = all_markers_freq.get(term, 0) + 1

        stats_by_source = {}
        for src, arts in by_source.items():
            if arts:
                scores = [a["polarization"]["score"] for a in arts]
                avg_score = round(sum(scores) / len(scores), 1)
                
                # Distribución
                dist = {
                    "baja": len([s for s in scores if s <= 25]),
                    "moderada": len([s for s in scores if 26 <= s <= 50]),
                    "alta": len([s for s in scores if 51 <= s <= 74]),
                    "muy_alta": len([s for s in scores if s >= 75]),
                }
                
                profile = NEWSPAPER_PROFILES.get(src, {})
                stats_by_source[src] = {
                    "name": src,
                    "count": len(arts),
                    "avg_score": avg_score,
                    "distribution": dist,
                    "profile": profile
                }
            else:
                stats_by_source[src] = {
                    "name": src,
                    "count": 0,
                    "avg_score": 0,
                    "distribution": {"baja": 0, "moderada": 0, "alta": 0, "muy_alta": 0},
                    "profile": NEWSPAPER_PROFILES.get(src, {})
                }

        # Top 10 palabras polarizantes más frecuentes hoy
        sorted_markers = sorted(all_markers_freq.items(), key=lambda x: x[1], reverse=True)[:10]

        return {
            "total_articles": len(articles),
            "last_updated": datetime.fromtimestamp(self._last_fetch_time, tz=timezone.utc).isoformat() if self._last_fetch_time else None,
            "sources": stats_by_source,
            "top_polarized_terms": [{"term": t, "count": c} for t, c in sorted_markers]
        }

fetcher = NewsFetcher()
