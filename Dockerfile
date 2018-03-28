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

# Permission issues with volumes otherwise
RUN gpg --keyserver ha.pool.sks-keyservers.net --recv-keys B42F6819007F00F88E364FD4036A9C25BF357DD4
RUN curl -o /usr/local/bin/gosu -SL "https://github.com/tianon/gosu/releases/download/1.4/gosu-$(dpkg --print-architecture)" \
    && curl -o /usr/local/bin/gosu.asc -SL "https://github.com/tianon/gosu/releases/download/1.4/gosu-$(dpkg --print-architecture).asc" \
    && gpg --verify /usr/local/bin/gosu.asc \
    && rm /usr/local/bin/gosu.asc \
    && chmod +x /usr/local/bin/gosu \
    && gosu nobody true

RUN python3.6 -m pip install -U --process-dependency-links red-discordbot[voice]

WORKDIR /home/red

COPY ./docker/basic-config.json /home/red/.config/Red-DiscordBot/config.json
COPY ./docker/run_red.sh /home/red/run_red.sh

# more permission needed things
COPY ./docker/entrypoint.sh /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]

# This is overriden in compose.yml, but is needed in standalone
CMD python3.6 -m redbot docker