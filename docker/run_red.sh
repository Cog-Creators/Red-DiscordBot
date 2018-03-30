#!/bin/sh
export RED_TOKEN=$(cat /run/secrets/RED_TOKEN)
export PREFIX=$(cat /run/secrets/PREFIX)
export HOME=/home/red
python3 -m redbot docker --no-prompt --dev --mentionable --prefix ${PREFIX}