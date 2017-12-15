FROM python:slim 

# Dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    git \
    libav-tools \
    libffi-dev \
    libopus-dev \
    libssl-dev \
    make \
    unzip \
    && rm -rf /var/lib/apt/lists/*

# Setup Redbot

RUN python3.6 -m pip install -U --process-dependency-links red-discordbot[voice]
RUN redbot-setup-docker

# Run Redbot
CMD redbot red --no-prompt --prefix $PREFIX