FROM python:3.12-slim as base

WORKDIR /app

COPY ./requirements.txt .

RUN pip install --no-cache-dir --upgrade -r requirements.txt

COPY ./src ./src

FROM base as dev

CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "80", "--reload"]

FROM base as final

CMD ["uvicorn", "src.server:app", "--host", "0.0.0.0", "--port", "80"]
