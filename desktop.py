#!/usr/bin/env python3
"""
Lanzador de escritorio nativo para macOS usando pywebview y WKWebView.
Inicia el servidor Flask en segundo plano y muestra una ventana nativa de macOS.
"""

import sys
import os
import time
import socket
import threading
import urllib.request

# Asegurar path correcto
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from app import app
from fetcher import fetcher

def is_port_in_use(port: int) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('127.0.0.1', port)) == 0

def wait_for_server(url: str, timeout: float = 8.0) -> bool:
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            with urllib.request.urlopen(url, timeout=1) as response:
                if response.status == 200:
                    return True
        except Exception:
            time.sleep(0.2)
    return False

def start_flask(port: int):
    # Pre-cargar artículos
    fetcher.get_articles()
    app.run(host='127.0.0.1', port=port, debug=False, use_reloader=False)

def main():
    port = 5050
    if not is_port_in_use(port):
        # Iniciar servidor Flask en hilo secundario
        server_thread = threading.Thread(target=start_flask, args=(port,), daemon=True)
        server_thread.start()
        print(f"[Desktop] Servidor Flask iniciado en el puerto {port}...")
    else:
        print(f"[Desktop] Servidor ya activo en el puerto {port}, reutilizando...")

    url = f"http://127.0.0.1:{port}"
    wait_for_server(url)

    try:
        import webview
        # Crear ventana nativa de macOS
        window = webview.create_window(
            title="POLARIS — Monitor de Noticias y Polarización",
            url=url,
            width=1320,
            height=880,
            min_size=(960, 640),
            confirm_close=False,
            text_select=True
        )
        webview.start()
    except Exception as e:
        print(f"[Desktop] Error al iniciar webview nativo: {e}")
        # Fallback: abrir en el navegador predeterminado
        import webbrowser
        webbrowser.open(url)

if __name__ == "__main__":
    main()
