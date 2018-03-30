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
    
COPY ./docker/basic-config.json /home/red/.config/Red-DiscordBot/config.json
COPY ./docker/run_red.sh /home/red/run_red.sh

RUN echo "red:x:1000:1000::/home/red:" >> /etc/passwd && \
    echo "red:!:$(($(date +%s) / 60 / 60 / 24)):0:99999:7:::" >> /etc/shadow && \
    echo "red:x:1000:" >> /etc/group && \
    chmod +x /home/red/run_red.sh && \
    chown red:red /home/red

USER red

CMD python3 -m redbot docker