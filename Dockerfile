FROM python:3.6.4-jessie

RUN echo deb "http://http.debian.net/debian jessie-backports main" >> /etc/apt/sources.list && \
    apt-get update \
    && apt install -y -t jessie-backports openjdk-8-jre-headless ca-certificates-java \
    && /usr/sbin/update-java-alternatives -s java-1.8.0-openjdk-amd64 \
    && apt-get install -y --no-install-recommends \
    git \
    unzip \
    sudo \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

RUN python3.6 -m pip install -U --process-dependency-links red-discordbot[voice]

RUN useradd --create-home --shell /bin/bash red && adduser red sudo && \
    echo "$(id red -gn) ALL = (ALL) NOPASSWD: ALL" >> /etc/sudoers
USER red
WORKDIR /home/red

COPY ./docker/basic-config.json /home/red/.config/Red-DiscordBot/config.json
COPY ./docker/run_red.sh /home/red/run_red.sh
RUN sudo chown -R red:red /home/red && chmod 755 /home/red/run_red.sh

# This is overriden in compose.yml, but is needed in standalone
CMD sudo chown -R red:red /home/red && \
    python3.6 -m redbot docker