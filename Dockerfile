FROM debian:buster

MAINTAINER Sandro Jäckel <sandro.jaeckel@gmail.com>

WORKDIR /app

COPY ["docker/config.json", "/root/.config/Red-DiscordBot/"]

RUN apt-get update \
  && apt-get install --no-install-recommends -y build-essential default-jre-headless git libffi-dev libssl-dev python3-dev python3-pip python3-setuptools unzip wget zip\
  && pip3 install -U --process-dependency-links --no-cache-dir git+https://github.com/Cog-Creators/Red-DiscordBot/archive/V3/develop.tar.gz#egg=Red-DiscordBot[voice] \
  && rm ~/.cache/pip -rf \
  && apt-get remove -y build-essential \
  && apt-get autoremove \
  && rm -rf /var/lib/apt/lists/*

CMD [ "redbot", "docker" ]
