FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11 as base

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY ./requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

COPY ./ /app/
WORKDIR /app/

ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite:///data/db.sqlite

EXPOSE 80

CMD ["/start.sh"]
