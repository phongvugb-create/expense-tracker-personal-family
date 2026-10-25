FROM python:3.12-alpine

WORKDIR /app

COPY exporter.py /app/exporter.py

ENV PYTHONUNBUFFERED=1 \
    LISTEN_PORT=9417 \
    CONTAINER_PREFIX=expense_tracker_ \
    SCRAPE_INTERVAL=3.0

EXPOSE 9417

CMD ["python", "/app/exporter.py"]
