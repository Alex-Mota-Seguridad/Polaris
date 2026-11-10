"""
Servidor web y API REST para el Agregador de Noticias y Analizador de Polarización.
Cabeceras analizadas: El País, El Mundo, El Confidencial, ABC.
"""

from flask import Flask, render_template, request, jsonify
from fetcher import fetcher
from clusterer import clusterer
from analyzer import analyzer, NEWSPAPER_PROFILES
from reader import extract_article

app = Flask(__name__, static_folder="static", template_folder="templates")

@app.route("/")
def index():
    """Página principal de la aplicación."""
    return render_template("index.html", profiles=NEWSPAPER_PROFILES)

@app.route("/api/news", methods=["GET"])
def get_news():
    """Devuelve listado de noticias filtradas, buscadas y ordenadas con metadatos de polarización."""
    source_filter = request.args.get("source", "all").strip()
    level_filter = request.args.get("level", "all").strip().lower()
    query = request.args.get("q", "").strip().lower()
    sort_by = request.args.get("sort", "latest").strip()
    limit = int(request.args.get("limit", 60))
    offset = int(request.args.get("offset", 0))

    articles = fetcher.get_articles()

    # Filtro por medio
    if source_filter != "all":
        sources_allowed = [s.strip() for s in source_filter.split(",")]
        articles = [a for a in articles if a["source"] in sources_allowed]

    # Filtro por nivel de polarización
    if level_filter != "all":
        articles = [a for a in articles if a["polarization"]["level_slug"] == level_filter]

    # Búsqueda por palabra clave
    if query:
        articles = [
            a for a in articles
            if query in a["title"].lower() 
            or query in a["description"].lower() 
            or query in a.get("author", "").lower()
        ]

    # Ordenación
    if sort_by == "pol_desc":
        articles.sort(key=lambda a: a["polarization"]["score"], reverse=True)
    elif sort_by == "pol_asc":
        articles.sort(key=lambda a: a["polarization"]["score"])
    else:  # latest
        articles.sort(key=lambda a: a["published_timestamp"], reverse=True)

    total_matched = len(articles)
    paginated = articles[offset:offset + limit]

    return jsonify({
        "total": total_matched,
        "offset": offset,
        "limit": limit,
        "articles": paginated
    })

@app.route("/api/topics", methods=["GET"])
def get_topics():
    """Devuelve temas agrupados entre múltiples periódicos y su brecha de polarización."""
    articles = fetcher.get_articles()
    clusters = clusterer.cluster_articles(articles)
    return jsonify({
        "total_clusters": len(clusters),
        "clusters": clusters
    })

@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Devuelve estadísticas agregadas y distribución de polarización por periódico."""
    stats = fetcher.get_stats()
    return jsonify(stats)

@app.route("/api/refresh", methods=["POST"])
def refresh_news():
    """Fuerza la recarga inmediata de todos los feeds RSS/Atom."""
    fetcher.get_articles(force_refresh=True)
    stats = fetcher.get_stats()
    return jsonify({
        "status": "success",
        "message": "Feeds actualizados correctamente.",
        "stats": stats
    })

@app.route("/api/reader", methods=["GET"])
def get_reader_content():
    """Extrae el contenido completo y limpio de un artículo para lectura directa en la app."""
    url = request.args.get("url", "").strip()
    if not url:
        return jsonify({"status": "error", "message": "Falta el parámetro url"}), 400
    
    data = extract_article(url)
    return jsonify(data)

@app.route("/api/analyze", methods=["POST"])
def analyze_custom():
    """Analiza en tiempo real cualquier titular o texto introducido por el usuario."""
    data = request.get_json(silent=True) or {}
    text = data.get("text", "").strip()
    source = data.get("source", "").strip()

    if not text:
        return jsonify({"error": "Debes proporcionar un texto para analizar"}), 400

    analysis = analyzer.analyze(title=text, description="", source=source)
    return jsonify({
        "text": text,
        "analysis": analysis
    })

if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 5050))
    host = os.environ.get("HOST", "127.0.0.1")
    print("[Server] Iniciando descarga y análisis de noticias...")
    fetcher.get_articles()
    print(f"[Server] Listo. Servidor en ejecución en http://{host}:{port}")
    app.run(host=host, port=port, debug=False)
