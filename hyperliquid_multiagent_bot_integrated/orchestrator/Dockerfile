FROM python:3.11-slim

WORKDIR /app

# Copia la cartella shared dal livello superiore
COPY ../shared ./shared

# Copia tutto il contenuto della cartella orchestrator
COPY . .

# Installa requirements
RUN pip install --no-cache-dir -r requirements.txt

# Avvia FastAPI
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
