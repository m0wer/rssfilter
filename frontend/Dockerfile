FROM python:3.11-slim as base

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    software-properties-common \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip3 install -r requirements.txt


EXPOSE 8501
HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

COPY . .

FROM base as dev

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--browser.gatherUsageStats=False", "--logger.level=debug", "--server.enableCORS=false"]

FROM base as final

ENTRYPOINT ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0", "--browser.gatherUsageStats=False", "--logger.level=debug"]
