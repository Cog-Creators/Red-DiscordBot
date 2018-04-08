#!/bin/sh
if [ -f /run/secrets/RED_TOKEN ]; then
  export RED_TOKEN=$(cat /run/secrets/RED_TOKEN)
fi
if [ -f /run/secrets/PREFIX ]; then
  export PREFIX=$(cat /run/secrets/PREFIX)
fi
export HOME=/home/red
python3 -m redbot docker --no-prompt --dev --mentionable --prefix ${PREFIX}