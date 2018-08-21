FROM python:python3.7.0-alpine3.8

RUN apk add --no-cache \
    openjdk8-jre \
    unzip \
    gcc \  
    git && \
    pip3 install --upgrade pip setuptools

ADD . /app
WORKDIR /app
RUN mkdir /data && \
    mkdir -p /root/.local/share && \
    ln -s /data /root/.local/share/Red-DiscordBot
RUN mv /app/docker/base-config.json /root/.config/Red-DiscordBot/config.json

RUN pip3 install -e .[voice, mongo] --process-dependency-links

