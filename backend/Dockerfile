FROM tiangolo/uvicorn-gunicorn-fastapi:python3.10 as base
FROM pytorch/pytorch:2.2.1-cuda12.1-cudnn8-runtime as runner
# when updating these iamges:
# - make sure the python versions match
# - upgrade the torch version in the requirements file

COPY --from=base /start-reload.sh /start-reload.sh
COPY --from=base /start.sh /start.sh
COPY --from=base /gunicorn_conf.py /gunicorn_conf.py

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY ./requirements.in /app/requirements.in
RUN pip install --no-cache-dir -r /app/requirements.in

COPY ./ /app/
WORKDIR /app/

ENV PYTHONPATH=/app
ENV DATABASE_URL=sqlite:///data/db.sqlite

EXPOSE 80

CMD ["/start.sh"]
