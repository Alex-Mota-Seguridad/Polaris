# POLARIS — Agregador de Noticias & Monitor de Polarización

Agregador de prensa digital en tiempo real para cuatro de las principales cabeceras españolas:
- **El País** (Centro-izquierda / Progresista)
- **El Confidencial** (Centro / Liberal independiente)
- **El Mundo** (Centro-derecha / Liberal-conservador)
- **ABC** (Derecha / Conservador monárquico)

---

## 🚀 Inicio Rápido

Para iniciar la aplicación en tu navegador:

```bash
cd /Users/mota/.gemini/antigravity/scratch/news-aggregator-polarizacion
./run.sh
```

O directamente con Python:

```bash
python3 app.py
```

Luego abre en tu navegador: **[http://127.0.0.1:5050](http://127.0.0.1:5050)**

---

## 🎯 Características Principales

1. **Feed Unificado en Tiempo Real**:
   - Agrega más de 350 artículos en directo desde los feeds oficiales RSS/Atom de los 4 periódicos.
   - Filtro instantáneo por diario (activar/desactivar cabeceras con un clic).
   - Buscador por texto, tema o autor con respuesta instantánea.
   - Filtro por nivel de polarización (*Baja, Moderada, Alta, Muy Alta*).
   - Ordenación por fecha más reciente o por índice de polarización.

2. **Índice de Polarización (0 a 100)**:
   - **0 a 25 — Baja (Verde)**: Registro fáctico, descriptivo y neutro.
   - **26 a 50 — Moderada (Azul)**: Tono periodístico con leve adjetivación o encuadre de fondo.
   - **51 a 74 — Alta (Ámbar)**: Carga valorativa notable, vocabulario de confrontación, alarma o framing ideológico.
   - **75 a 100 — Muy Alta (Rojo)**: Titulares de combate político, hipérboles, belicismo discursivo o sesgo partidista explícito.
   - **Modal de desglose detallado**: Haz clic en cualquier tarjeta para ver qué términos exactos activaron la puntuación, el uso de comillas de distanciamiento, preguntas retóricas y el diagnóstico cualitativo.

3. **Comparador de Temas (Cobertura Cruzada Lado a Lado)**:
   - Algoritmo de agrupamiento temático que detecta cuándo 2, 3 o los 4 diarios cubren el **mismo acontecimiento**.
   - Muestra los titulares en paralelo ordenados en el espectro político (de izquierda a derecha).
   - Calcula la **Brecha de Polarización ($\Delta$)**, indicando si la cobertura es homogénea o si existe una fuerte discrepancia de encuadre.

4. **Radar de Medios & Estadísticas**:
   - Gráfico de **Brújula Editorial vs Polarización Media** (Chart.js) que posiciona a cada cabecera según su eje ideológico histórico y el tono promedio de sus noticias hoy.
   - Gráfico de distribución de tono por periódico.
   - Ranking de los términos y conceptos polarizantes más repetidos en la jornada.

5. **Laboratorio de Análisis en Directo**:
   - Permite escribir o pegar cualquier titular o declaración para evaluarla al instante con el motor de polarización.

---

## 🔬 Metodología de Análisis de Polarización

El analizador lingüístico (`analyzer.py`) evalúa 6 dimensiones clave:
1. **Belicismo verbal y confrontación**: Verbos y expresiones de combate (*arremete, fulmina, pulveriza, acorrala, dinamita, trinchera, guerra sucia, asedio*).
2. **Alarma y catastrofismo**: Términos de pánico y debacle (*caos, catástrofe, hecatombe, ruina, agoniza, colapso, dantesco*).
3. **Juicio moral e indignación**: Palabras de deslegitimación ética (*escándalo, farsa, vergüenza, bochorno, traición, chantaje, cloacas, mafia*).
4. **Framing ideológico de derecha**: Carga semántica contra el gobierno o pactos (*sanchismo, golpistas, separatismo, cesiones, amnistía vergonzosa, expolio fiscal*).
5. **Framing ideológico de izquierda**: Carga semántica contra la derecha (*ultraderecha, negacionismo, máquina del fango, lawfare, recortes salvajes*).
6. **Recursos retóricos de titular**: Comillas peyorativas/irónicas, preguntas retóricas de sospecha y mayúsculas de urgencia.

---

## 📁 Estructura del Proyecto

```text
news-aggregator-polarizacion/
├── app.py                # Servidor Flask y endpoints API REST
├── fetcher.py            # Descargador paralelo de feeds RSS/Atom con caché en memoria
├── analyzer.py           # Motor de análisis léxico, retórico y espectro de polarización
├── clusterer.py          # Agrupador de noticias sobre el mismo evento y cálculo de brechas
├── run.sh                # Script ejecutable de inicio rápido
├── templates/
│   └── index.html        # Interfaz web interactiva (Tailwind CSS, Chart.js, Vanilla JS)
└── README.md             # Documentación del proyecto
```
