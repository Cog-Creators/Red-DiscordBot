FROM python:3.6.4-jessie

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
    git \
    unzip \
    default-jre \
    sudo \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN python3.6 -m pip install -U --process-dependency-links red-discordbot[voice]

RUN useradd --create-home --shell /bin/bash red && adduser red sudo && \
    echo "$(id red -gn) ALL = (ALL) NOPASSWD: ALL" >> /etc/sudoers
USER red
WORKDIR /home/red

COPY ./docker/basic-config.json /home/red/.config/Red-DiscordBot/config.json

CMD sudo chown -R red:red /home/red && \
    python3.6 -m redbot docker --no-prompt --dev --mentionable