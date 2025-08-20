FROM python:3.9-slim

# Installa le dipendenze
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Copia il codice dell'app
COPY . .

# Imposta la porta ed esegue l'app Streamlit
EXPOSE 8501
CMD ["streamlit", "run", "app/web/streamlit_app.py", "--server.port=8501", "--server.enableCORS=false"]
