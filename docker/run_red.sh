#!/bin/bash
export RED_TOKEN=$(cat /run/secrets/RED_TOKEN)
export PREFIX=$(cat /run/secrets/PREFIX)
python3.6 -m redbot docker --no-prompt --dev --mentionable --prefix ${PREFIX}