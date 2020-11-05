FROM python:3-slim
MAINTAINER x0rzkov <x0rzkov@protonmail.com>

RUN apt-get update && \
    apt-get install -y ca-certificates git nano bash docker.io && \
    python3 -m pip install -U pip && \
    pip3 install celery && \
    pip3 install flask && \
    pip3 install redis

WORKDIR /opt/service

COPY . .

CMD ["/bin/bash"]
