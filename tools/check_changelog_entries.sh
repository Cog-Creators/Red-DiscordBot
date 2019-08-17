#!/usr/bin/env bash

# This can be run for other remotes than origin with the env vat `RED_REMOTE`
REMOTE="${RED_REMOTE:-origin}"

if [[ $(git diff "$REMOTE"/V3/develop) ]]; then

  if [[ $(git diff "$REMOTE"/V3/develop -- changelog.d/) ]]; then
    echo "Found changelog fragments..."
    exit 0
  else
    echo "Error: No new changelog fragments!"
    exit 1
  fi

else
  echo "No changes to need changelog for."
  exit 0
fi
