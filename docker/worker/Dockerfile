FROM mcr.microsoft.com/playwright/python:v1.49.1-noble
LABEL org.opencontainers.image.source https://github.com/mbroton/browsy

ARG VERSION

WORKDIR /worker

RUN pip install "browsy[worker]==${VERSION}"

RUN adduser --uid 1266 --disabled-password --gecos '' browsyuser && \
    addgroup --gid 1267 browsygroup && \
    usermod -a -G browsygroup browsyuser

RUN mkdir -p /data && chown -R browsyuser:browsygroup /data
