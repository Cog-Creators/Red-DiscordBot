FROM python:3.7-slim-stretch

WORKDIR /app
ENV LD_LIBRARY_PATH /usr/local/lib:/usr/lib

RUN apt-get update && \
    apt-get dist-upgrade -y && \
    apt-get install -y --no-install-recommends git ca-certificates xz-utils libssl-dev build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/* && \
    pip install -U pip Cython pytest -q --retries 30 && \
    rm -rf /root/.cache/pip/*

COPY . /red_src/

RUN \
    pip install -U /red_src[mongo] && \
    rm -rf /root/.cache/pip/* && \
    rm -rf /red_src/ && \
    find /usr/local -depth \
        \( \
            \( -type d -a \( -name test -o -name tests \) \) \
            -o \
            \( -type f -a \( -name '*.pyc' -o -name '*.pyo' \) \) \
        \) -exec rm -rf '{}' +

COPY docker/red-mongodb/config.json /root/.config/Red-DiscordBot/

ENTRYPOINT [ "python", "-m", "redbot", "docker" ]
