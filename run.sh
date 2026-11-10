#!/usr/bin/env bash
# Script de inicio para POLARIS - Agregador de Noticias y Monitor de Polarización
cd "$(dirname "$0")"

echo "=========================================================="
echo "  POLARIS | Agregador de Noticias & Monitor de Polarización"
echo "  Diarios: El País, El Mundo, El Confidencial, ABC"
echo "=========================================================="
echo ""

# Comprobar python3
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 no está instalado en tu sistema."
    exit 1
fi

echo "Iniciando servidor web..."
echo "Abre tu navegador en: http://127.0.0.1:5050"
echo "Pulsa Ctrl+C para detener el servidor."
echo ""

python3 app.py
