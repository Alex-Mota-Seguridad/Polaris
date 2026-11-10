"""
Módulo de agrupamiento de noticias y comparador de enfoques editoriales (Cross-Media Topic Clustering).
Identifica cuándo 2 o más diarios (El País, El Mundo, El Confidencial, ABC) están cubriendo
el mismo hecho noticioso y calcula la brecha de polarización y divergencia de encuadre.
"""

import re
from typing import List, Dict, Any, Set
from analyzer import normalize_text, NEWSPAPER_PROFILES

STOPWORDS = set([
    'de', 'la', 'que', 'el', 'en', 'y', 'a', 'los', 'del', 'se', 'las', 'por', 'un', 'una', 'su',
    'al', 'lo', 'como', 'mas', 'pero', 'sus', 'le', 'ya', 'o', 'este', 'si', 'porque', 'esta',
    'entre', 'cuando', 'muy', 'sin', 'sobre', 'tambien', 'me', 'hasta', 'hay', 'donde', 'quien',
    'desde', 'todo', 'nos', 'durante', 'todos', 'uno', 'les', 'ni', 'contra', 'otros', 'ese',
    'eso', 'ante', 'ellos', 'e', 'esto', 'tras', 'dia', 'dias', 'ano', 'anos', 'nuevo', 'nueva',
    'gran', 'tres', 'dos', 'cuatro', 'cinco', 'primer', 'primera', 'segun', 'cada', 'estos', 'estas',
    'tras', 'menos', 'hacia', 'puede', 'pueden', 'ser', 'sido', 'tener', 'tiene', 'tienen', 'haber',
    'habia', 'hace', 'hacer', 'dice', 'dicen', 'tras el', 'tras la'
])

def extract_tokens(text: str) -> Set[str]:
    """Extrae palabras clave significativas eliminando stopwords y palabras cortas."""
    norm = normalize_text(text)
    words = re.findall(r'\b[a-z]{3,}\b', norm)
    return set(w for w in words if w not in STOPWORDS)

class TopicClusterer:
    def __init__(self):
        pass

    def cluster_articles(self, articles: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Agrupa noticias que traten sobre el mismo acontecimiento y calcula
        las métricas comparativas de polarización y brecha editorial.
        """
        clusters: List[Dict[str, Any]] = []
        assigned_ids = set()

        # Orden ideológico para presentar las noticias ordenadas de izquierda a derecha
        source_order = {
            "El País": -0.45,
            "El Confidencial": 0.08,
            "El Mundo": 0.45,
            "ABC": 0.70
        }

        for i, art_a in enumerate(articles):
            if art_a["id"] in assigned_ids:
                continue

            tokens_a = extract_tokens(art_a["title"])
            if len(tokens_a) < 2:
                continue

            cluster_articles = [art_a]
            sources_in_cluster = {art_a["source"]}
            shared_keywords_all = set(tokens_a)

            for j, art_b in enumerate(articles[i + 1:], start=i + 1):
                if art_b["id"] in assigned_ids:
                    continue

                tokens_b = extract_tokens(art_b["title"])
                if len(tokens_b) < 2:
                    continue

                shared = tokens_a.intersection(tokens_b)
                overlap = len(shared)
                union_len = len(tokens_a.union(tokens_b))
                jaccard = overlap / union_len if union_len > 0 else 0

                # Criterio de coincidencia temática: al menos 3 palabras compartidas o 2 con alto solapamiento
                if (overlap >= 3) or (overlap == 2 and jaccard >= 0.28):
                    cluster_articles.append(art_b)
                    sources_in_cluster.add(art_b["source"])
                    shared_keywords_all = shared_keywords_all.intersection(tokens_b) if shared_keywords_all else shared

            # Solo nos interesan historias con cobertura cruzada (al menos 2 diarios distintos)
            if len(sources_in_cluster) >= 2:
                for a in cluster_articles:
                    assigned_ids.add(a["id"])

                # Ordenar artículos del clúster de izquierda a derecha política
                cluster_articles.sort(key=lambda x: source_order.get(x["source"], 0))

                # Métricas de polarización dentro del clúster
                scores = [a["polarization"]["score"] for a in cluster_articles]
                max_score = max(scores)
                min_score = min(scores)
                gap = max_score - min_score
                avg_score = round(sum(scores) / len(scores), 1)

                # Evaluación de divergencia
                if gap >= 35:
                    assessment = "Brecha Alta: Fuerte discrepancia de tono o encuadre ideológico entre las cabeceras."
                    gap_level = "alta"
                elif gap >= 18:
                    assessment = "Brecha Moderada: Discrepancia apreciable en la adjetivación o enfoque del titular."
                    gap_level = "moderada"
                else:
                    assessment = "Convergencia Fáctica: Cobertura homogénea y descriptiva en los diferentes medios."
                    gap_level = "baja"

                # Título representativo del tema: elegimos el más neutral o completo
                representative_title = min(cluster_articles, key=lambda x: (x["polarization"]["score"], -len(x["title"])))["title"]

                clusters.append({
                    "id": f"cluster_{len(clusters)+1}_{abs(hash(representative_title))}",
                    "title": representative_title,
                    "sources_count": len(sources_in_cluster),
                    "articles_count": len(cluster_articles),
                    "sources": list(sources_in_cluster),
                    "articles": cluster_articles,
                    "polarization_gap": gap,
                    "avg_polarization": avg_score,
                    "gap_level": gap_level,
                    "assessment": assessment,
                    "keywords": list(tokens_a)[:5]
                })

        # Ordenar clústeres por número de medios (mayor cobertura cruzada primero), luego por brecha
        clusters.sort(key=lambda c: (c["sources_count"], c["polarization_gap"]), reverse=True)
        return clusters

clusterer = TopicClusterer()
