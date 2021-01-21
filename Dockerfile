FROM python:3-slim

RUN apt-get update && \
    apt-get install -y ca-certificates git vim bash docker.io && \
    python3 -m pip install -U pip && \
    pip3 install flask && \
    pip3 install celery[redis] && \
    pip3 install pymongo

WORKDIR /opt/service

COPY . .
