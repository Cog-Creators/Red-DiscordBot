#!/bin/sh

set -e

if [ -n "$BOT_TOKEN_FILE" ]; then BOT_TOKEN="$(cat $BOT_TOKEN_FILE)"; fi

redbot docker --no-prompt --token $BOT_TOKEN --prefix $BOT_PREFIX "$@"
