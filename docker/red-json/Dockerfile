FROM python:3.7-slim-buster

WORKDIR /app
ENV LD_LIBRARY_PATH /usr/local/lib:/usr/lib

RUN apt-get update && \
    apt-get install -y --no-install-recommends git ca-certificates xz-utils libssl-dev build-essential && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

COPY . /red_src/
COPY docker/red-json/config.json /root/.config/Red-DiscordBot/

RUN pip install -U pip Cython pytest /red_src --retries 3 && \
    rm -rf /root/.cache/pip/* /red_src/ && \
    find /usr/local -depth \
        \( \
            \( -type d -a \( -name test -o -name tests \) \) \
            -o \
            \( -type f -a \( -name '*.pyc' -o -name '*.pyo' \) \) \
        \) -exec rm -rf '{}' +

ENTRYPOINT [ "python", "-m", "redbot", "docker" ]
