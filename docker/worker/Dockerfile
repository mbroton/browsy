FROM mcr.microsoft.com/playwright/python:v1.49.1-noble
LABEL org.opencontainers.image.source https://github.com/mbroton/browsy

ARG VERSION

WORKDIR /worker

RUN apt-get update && apt-get install -y python3 python3-pip

RUN pip install "browsy[worker]==${VERSION}"
