FROM alpine:3.7

RUN apk add --no-cache \
    python3 \
    openjdk8-jre \
    git \
    unzip && \
    python3 -m ensurepip && \
    rm -r /usr/lib/python*/ensurepip && \
    pip3 install --upgrade pip setuptools && \ 
    python3.6 -m pip install -U --process-dependency-links red-discordbot[voice] && \
    rm -r /root/.cache

# Don't actually run redbot-setup    
COPY ./docker/basic-config.json /home/red/.config/Red-DiscordBot/config.json
# Compose compatability (mongo later)
COPY ./docker/run_red.sh /home/red/run_red.sh

# Mounted FS Host Permissions.
ENV UID 1000
RUN echo "red:x:$UID:$UID::/home/red:" >> /etc/passwd && \
    echo "red:!:$(($(date +%s) / 60 / 60 / 24)):0:99999:7:::" >> /etc/shadow && \
    echo "red:x:$UID:" >> /etc/group && \
    chmod +x /home/red/run_red.sh && \
    mkdir /data && \
    mkdir -p /home/red/.local/share && \
    ln -s /data /home/red/.local/share/Red-DiscordBot && \
    chown red:red /home/red
USER red

CMD python3 -m redbot docker --no-prompt --dev --mentionable --prefix ${PREFIX}