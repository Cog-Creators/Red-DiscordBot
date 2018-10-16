FROM python:3.7-alpine

WORKDIR /app
ENV LD_LIBRARY_PATH /usr/local/lib:/usr/lib

RUN echo "http://dl-8.alpinelinux.org/alpine/edge/community" >> /etc/apk/repositories

RUN \
    apk --no-cache add -q git openssl openssl-dev openssh alpine-sdk build-base gnupg linux-headers xz && \
    pip install -U pip Cython pytest -q --retries 30

COPY . /red_src/

RUN \
    pip install -U /red_src && \
    rm -rf /root/.cache/pip/* && \
    rm -rf /var/cache/apk/* && \
    rm -rf /red_src/ && \
    find /usr/local -depth \
        \( \
            \( -type d -a \( -name test -o -name tests \) \) \
            -o \
            \( -type f -a \( -name '*.pyc' -o -name '*.pyo' \) \) \
        \) -exec rm -rf '{}' +

COPY docker/red-json/config.json /root/.config/Red-DiscordBot/

ENTRYPOINT [ "python", "-m", "redbot", "docker" ]
