# Speccify Web-Board (Spec 032): one container per board.
#   docker build -f apps/board/Dockerfile -t speccify-board .
#   docker run -p 8790:8790 -v $PWD/board.yaml:/config/board.yaml:ro -v board-data:/data speccify-board
FROM python:3.12-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends git ca-certificates openssh-client \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
COPY core /src/core
COPY apps/board /src/apps/board
RUN pip install --no-cache-dir /src/core /src/apps/board

ENV BOARD_CONFIG=/config/board.yaml \
    BOARD_DATA=/data \
    BOARD_HOST=0.0.0.0 \
    BOARD_PORT=8790
EXPOSE 8790

# Unprivileged user; mount an SSH key to /home/board/.ssh for git@ URLs.
# `VOLUME` comes last: layers after it could not change the folder's owner.
RUN useradd --create-home --uid 10001 board && mkdir -p /data /config && chown -R board:board /data /config
USER board
# Data (register clones) and config live outside the image.
VOLUME ["/data", "/config"]
HEALTHCHECK --interval=60s --timeout=5s CMD python -c "import urllib.request,sys;sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8790/healthz').status==200 else 1)"

CMD ["speccify-board"]
