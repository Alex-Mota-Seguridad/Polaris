"""
Módulo de análisis de polarización y sesgo informativo para medios de prensa españoles.
Evalúa titulares y noticias considerando:
- Carga emocional y adjetivación subjetiva
- Belicismo verbal y retórica de confrontación
- Marcadores de framing partidista e ideológico (izquierda/derecha)
- Recursos de sensacionalismo (comillas de distanciamiento, signos, hipérboles)
- Línea editorial histórica del medio
"""

import re
import unicodedata
from typing import Dict, List, Any, Optional

def normalize_text(text: str) -> str:
    """Elimina tildes y convierte a minúsculas para comparaciones léxicas robustas."""
    text = text.lower()
    text = unicodedata.normalize('NFD', text)
    text = ''.join(c for c in text if unicodedata.category(c) != 'Mn')
    return text

# Perfiles de los 4 diarios
NEWSPAPER_PROFILES = {
    "El País": {
        "slug": "elpais",
        "name": "El País",
        "publisher": "Grupo PRISA",
        "founded": "1976",
        "spectrum_label": "Centro-izquierda / Progresista",
        "spectrum_pos": -0.45,  # -1.0 (Izquierda radical) a +1.0 (Derecha radical)
        "color": "#1d4ed8",  # Azul institucional
        "badge_class": "bg-blue-100 text-blue-800 border-blue-200",
        "description": "Diario generalista de referencia histórica con orientación socialdemócrata, europeísta y progresista. Prioriza políticas sociales y derechos civiles."
    },
    "El Mundo": {
        "slug": "elmundo",
        "name": "El Mundo",
        "publisher": "Unidad Editorial",
        "founded": "1989",
        "spectrum_label": "Centro-derecha / Liberal-conservador",
        "spectrum_pos": 0.45,
        "color": "#0284c7",  # Cian / Celeste
        "badge_class": "bg-sky-100 text-sky-800 border-sky-200",
        "description": "Diario de referencia liberal-conservador, constitucionalista. Tradición de investigación crítica hacia gobiernos de izquierda y pactos con fuerzas soberanistas."
    },
    "El Confidencial": {
        "slug": "elconfidencial",
        "name": "El Confidencial",
        "publisher": "Titania Compañía Editorial",
        "founded": "2001",
        "spectrum_label": "Centro / Liberal independiente",
        "spectrum_pos": 0.08,
        "color": "#d97706",  # Ámbar / Dorado
        "badge_class": "bg-amber-100 text-amber-800 border-amber-200",
        "description": "Nativo digital de investigación, información económica, judicial y política. Enfoque analítico institucional, fiscalmente riguroso y plural."
    },
    "ABC": {
        "slug": "abc",
        "name": "ABC",
        "publisher": "Grupo Vocento",
        "founded": "1903",
        "spectrum_label": "Derecha / Conservador monárquico",
        "spectrum_pos": 0.70,
        "color": "#dc2626",  # Rojo clásico ABC
        "badge_class": "bg-red-100 text-red-800 border-red-200",
        "description": "Decano de la prensa conservadora en España. Defensor histórico de la Monarquía parlamentaria, la unidad nacional, las instituciones y el libre mercado."
    }
}

# Léxico de polarización categorizado
POLARIZATION_LEXICON = {
    # 1. Belicismo verbal y confrontación directa
    "confrontacion": {
        "weight": 3.0,
        "category_label": "Confrontación y belicismo verbal",
        "terms": [
            "arremete", "fulmina", "pulveriza", "acorrala", "aniquila", "aplasta",
            "asesta", "estalla", "revienta", "dinamita", "guerra sucia", "batalla campal",
            "asedio", "ofensiva", "linchamiento", "acoso y derribo", "embate", "hostil",
            "desafio total", "ultimatum", "machaca", "ajuste de cuentas", "purga",
            "fuego amigo", "trinchera", "declaracion de guerra", "fusilar", "choque frontal",
            "al abordaje", "masacre", "aplastante", "despedaza", "contraataca", "acorralado"
        ]
    },
    # 2. Emocionalidad intensa, alarma y catastrofismo
    "alarma_catastrofe": {
        "weight": 2.5,
        "category_label": "Alarma y catastrofismo",
        "terms": [
            "caos", "catastrofe", "hecatombe", "descalabro", "ruina", "apocalipsis",
            "panico", "asfixia", "drama", "pesadilla", "dantesco", "sangria", "derrumbe",
            "desastre", "naufragio", "debacle", "abismo", "al filo del abismo",
            "agoniza", "agonizante", "en coma", "tiempos oscuros", "alerta roja",
            "colapso", "bomba de relojeria", "infierno", "terror", "devastacion"
        ]
    },
    # 3. Juicio moral, indignación y deslegitimación
    "indignacion_moral": {
        "weight": 2.8,
        "category_label": "Juicio moral y deslegitimación",
        "terms": [
            "escandalo", "escandaloso", "farsa", "verguenza", "bochorno", "bochornoso",
            "ridiculo", "esperpento", "infamia", "aberracion", "disparate", "delirio",
            "traicion", "felonia", "chantaje", "cinismo", "cinico", "impunidad",
            "inmoral", "desfachatez", "bajeza", "vil", "miserable",
            "vergonzoso", "bravuconada", "hipocresia", "corruptelas", "mafia",
            "cloacas", "podredumbre", "inadmisible", "indecente", "humillante",
            "desverguenza", "fraude", "bochornosa"
        ]
    },
    # 4. Framing ideológico marcado: Derecha / Crítica frontal a la izquierda
    "framing_derecha": {
        "weight": 2.8,
        "category_label": "Encuadre crítico hacia el Gobierno / Pro-conservador",
        "terms": [
            "sanchismo", "separatismo", "separatista", "golpista", "golpismo",
            "filoterrorista", "herederos de eta", "ruptura de espana", "cesiones", "cesion",
            "chantaje independentista", "comunista", "bolivariano", "deriva autoritaria",
            "asalto a las instituciones", "colonizacion institucional", "dictadura",
            "okupacion", "expropiacion", "infierno fiscal", "expolio fiscal",
            "chiringuito", "paguiteros", "paguitas", "complice de terrorismo",
            "sumision", "arrodillado", "humillacion a espana", "amnistia vergonzosa"
        ]
    },
    # 5. Framing ideológico marcado: Izquierda / Crítica a la derecha y tradicionalismo
    "framing_izquierda": {
        "weight": 2.8,
        "category_label": "Encuadre ideológico progresista / Crítico con la derecha",
        "terms": [
            "ultraderecha", "extrema derecha", "fascismo", "fascista", "posfascista",
            "negacionismo", "negacionista", "maquina del fango", "cloacas del estado",
            "lawfare", "asedio judicial", "golpe judicial", "involucion", "recortes salvajes",
            "privatizacion salvaje", "tijeretazo", "patriarcado", "machismo institucional",
            "bulos de la derecha", "bulo", "bulocracia", "conspiranoico", "fuerzas reaccionarias",
            "nostalgicos del franquismo", "franquista", "caza de brujas"
        ]
    },
    # 6. Hipérboles absolutas y sensacionalismo
    "hiperboles": {
        "weight": 2.0,
        "category_label": "Hipérboles y superlativos absolutos",
        "terms": [
            "historico", "brutal", "demoledor", "implacable", "devastador", "fulminante",
            "colosal", "inaudito", "sin precedentes", "jamas visto", "nunca antes",
            "absoluto", "letal", "salvaje", "despiadado", "cruel", "monstruo",
            "monstruoso", "aplastante", "lapidario", "historica"
        ]
    }
}

def term_to_pattern(term: str) -> str:
    norm = normalize_text(term)
    if " " in norm:
        # Multi-palabra: escape literal con límites
        return r'\b' + re.escape(norm) + r'\b'
    # Inflecciones de género y número en español
    if norm.endswith(('o', 'a')):
        root = norm[:-1]
        return r'\b' + re.escape(root) + r'(?:o|a|os|as)\b'
    elif norm.endswith(('e', 'ista', 'dor')):
        return r'\b' + re.escape(norm) + r'(?:s|es)?\b'
    elif norm.endswith(('r', 'l', 'd', 'z', 'n')):
        return r'\b' + re.escape(norm) + r'(?:es|s)?\b'
    return r'\b' + re.escape(norm) + r'(?:s)?\b'

class PolarizationAnalyzer:
    def __init__(self):
        self.compiled_terms = []
        for cat_key, cat_data in POLARIZATION_LEXICON.items():
            for term in cat_data["terms"]:
                pattern_str = term_to_pattern(term)
                pattern = re.compile(pattern_str, re.IGNORECASE)
                self.compiled_terms.append((pattern, term, cat_key, cat_data["category_label"], cat_data["weight"]))

    def analyze(self, title: str, description: str = "", source: str = "") -> Dict[str, Any]:
        title = title or ""
        description = description or ""
        source = source or ""
        
        full_text = f"{title}. {description}"
        norm_full = normalize_text(full_text)
        norm_title = normalize_text(title)

        detected_markers = []
        seen_terms = set()
        total_lexical_points = 0.0
        
        category_scores = {
            "confrontacion": 0.0,
            "alarma_catastrofe": 0.0,
            "indignacion_moral": 0.0,
            "framing_derecha": 0.0,
            "framing_izquierda": 0.0,
            "hiperboles": 0.0
        }

        # Detección léxica
        for pattern, raw_term, cat_key, cat_label, weight in self.compiled_terms:
            title_match = pattern.search(norm_title)
            body_match = pattern.search(norm_full)
            
            if title_match or body_match:
                matched_str = title_match.group(0) if title_match else body_match.group(0)
                if matched_str not in seen_terms:
                    seen_terms.add(matched_str)
                    effective_weight = weight * 2.4 if title_match else weight
                    total_lexical_points += effective_weight
                    category_scores[cat_key] += effective_weight
                    
                    detected_markers.append({
                        "term": matched_str,
                        "base_term": raw_term,
                        "category": cat_key,
                        "category_label": cat_label,
                        "in_title": bool(title_match),
                        "weight": round(effective_weight, 1)
                    })

        # Marcadores retóricos y tipográficos en el titular
        rhetorical_points = 0.0
        rhetorical_cues = []

        # 1. Comillas de distanciamiento/ironía en el titular
        quotes = re.findall(r'["\'«»“”‘’][^"\'«»“”‘’]{2,30}["\'«»“”‘’]', title)
        if quotes:
            pts = min(len(quotes) * 4.5, 12.0)
            rhetorical_points += pts
            rhetorical_cues.append(f"Comillas de distanciamiento/énfasis: {', '.join(quotes[:2])}")

        # 2. Signos de exclamación o interrogación sospechosa en el titular
        if '!' in title or '¡' in title:
            rhetorical_points += 7.0
            rhetorical_cues.append("Exclamaciones de alerta o urgencia en el titular")
        if '?' in title or '¿' in title:
            rhetorical_points += 5.0
            rhetorical_cues.append("Pregunta retórica en titular")

        # 3. Mayúsculas enfáticas
        words = title.split()
        caps_words = [w for w in words if w.isupper() and len(w) > 3 and w not in ["PSOE", "PP", "VOX", "SUMAR", "PNV", "ERC", "BILDU", "JUNTS", "CNI", "OTAN", "UE", "ONU", "IPC", "PIB"]]
        if caps_words:
            rhetorical_points += 6.0
            rhetorical_cues.append(f"Mayúsculas enfáticas: {', '.join(caps_words[:2])}")

        # Puntuación base fáctica
        base_score = 10.0
        
        # Ponderación según materia política/controversial
        political_context = any(term in norm_full for term in [
            "sanchez", "feijoo", "abascal", "gobierno", "oposicion", "fiscal", "congreso",
            "tribunal supremo", "constitucional", "amnistia", "presupuestos", "elecciones",
            "corrupcion", "comision", "investigacion", "psoe", "pp", "vox"
        ])
        
        if political_context and (total_lexical_points > 0 or rhetorical_points > 0):
            context_multiplier = 1.3
        elif not political_context:
            context_multiplier = 0.85
        else:
            context_multiplier = 1.0

        raw_score = (base_score + (total_lexical_points * 2.6) + (rhetorical_points * 1.5)) * context_multiplier
        final_score = int(min(max(raw_score, 5), 100))

        # Determinar nivel cualitativo
        if final_score <= 25:
            level = "Baja"
            level_slug = "baja"
            badge_color = "emerald"
            level_desc = "Tono informativo fáctico, sobrio y descriptivo. Ausencia de lenguaje polarizante o juicios de valor marcados."
        elif final_score <= 50:
            level = "Moderada"
            level_slug = "moderada"
            badge_color = "sky"
            level_desc = "Tono periodístico estándar con encuadre editorial o adjetivación ligera, sin llegar a la confrontación."
        elif final_score <= 74:
            level = "Alta"
            level_slug = "alta"
            badge_color = "amber"
            level_desc = "Carga valorativa notable, presencia de términos de confrontación, alarma o framing ideológico apreciable."
        else:
            level = "Muy Alta"
            level_slug = "muy-alta"
            badge_color = "rose"
            level_desc = "Titular altamente polarizado, retórica beligerante, fuerte juicio de valor o sesgo partidista explícito."

        # Identificar orientación de sesgo léxico específico si existe
        framing_bias = "Neutro / Fáctico"
        derecha_pts = category_scores["framing_derecha"]
        izquierda_pts = category_scores["framing_izquierda"]
        if derecha_pts > 0 and derecha_pts > izquierda_pts:
            framing_bias = "Encuadre crítico hacia el Gobierno / Pro-conservador"
        elif izquierda_pts > 0 and izquierda_pts > derecha_pts:
            framing_bias = "Encuadre crítico hacia la derecha / Progresista"
        elif category_scores["confrontacion"] > 5:
            framing_bias = "Encuadre de confrontación institucional / Belicismo"
        elif category_scores["indignacion_moral"] > 5:
            framing_bias = "Encuadre de indignación moral y denuncia"

        # Perfil editorial del medio emisor
        source_profile = NEWSPAPER_PROFILES.get(source, {
            "name": source or "Medio general",
            "spectrum_label": "Prensa generalista",
            "spectrum_pos": 0.0,
            "color": "#64748b",
            "badge_class": "bg-slate-100 text-slate-800 border-slate-200",
            "description": ""
        })

        # Generar explicación en español
        explanation_parts = []
        if detected_markers:
            terms_str = ", ".join([f"'{m['term']}'" for m in detected_markers[:3]])
            explanation_parts.append(f"Se identificaron marcadores léxicos como {terms_str} ({len(detected_markers)} en total).")
        if rhetorical_cues:
            explanation_parts.append(f"Recursos retóricos: {'; '.join(rhetorical_cues)}.")
        if not detected_markers and not rhetorical_cues:
            explanation_parts.append("El lenguaje utilizado se mantiene en un registro neutro y fáctico sin adjetivos hiperbólicos ni términos de combate.")

        explanation = " ".join(explanation_parts)

        return {
            "score": final_score,
            "level": level,
            "level_slug": level_slug,
            "level_desc": level_desc,
            "badge_color": badge_color,
            "framing_bias": framing_bias,
            "detected_markers": detected_markers,
            "rhetorical_cues": rhetorical_cues,
            "category_scores": category_scores,
            "explanation": explanation,
            "source_profile": source_profile
        }

analyzer = PolarizationAnalyzer()
