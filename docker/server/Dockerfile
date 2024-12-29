FROM python:3.12-slim
ARG VERSION

LABEL org.opencontainers.image.source https://github.com/mbroton/browsy

WORKDIR /server

RUN pip install "browsy[server]==${VERSION}"

RUN adduser --uid 1266 --disabled-password --gecos '' browsyuser && \
    addgroup --gid 1267 browsygroup && \
    usermod -a -G browsygroup browsyuser

RUN mkdir -p /data && chown -R browsyuser:browsygroup /data

COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
