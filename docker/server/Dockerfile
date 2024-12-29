FROM python:3.12-slim
ARG VERSION

LABEL org.opencontainers.image.source https://github.com/mbroton/browsy

WORKDIR /server

RUN pip install "browsy[server]==${VERSION}"
