FROM python:3.11-slim

WORKDIR /app

# Instalar dependencias
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copiar código fuente
COPY . .

# Puerto por defecto
EXPOSE 5050
ENV PORT=5050

CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5050", "--workers", "2", "--timeout", "120"]
