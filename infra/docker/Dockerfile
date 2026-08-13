FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

COPY app /opt/nagstamon-headless
RUN pip install --no-cache-dir -r /opt/nagstamon-headless/requirements.txt \
    && pip install --no-cache-dir /opt/nagstamon-headless \
    && rm -rf /opt/nagstamon-headless

CMD ["nagstamon-headless"]
