#!/usr/bin/env bash

# This is hard coded as `origin` for the remote to check against for travis
# This should not be run elsewhere

if [[ ${TRAVIS:-false} = "true" ]]; then

  if [[ $(git diff origin/V3/develop) ]]; then

    if [[ $(git diff origin/V3/develop -- changelog.d/) ]]; then
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

else
  echo "We aren't on Travis, skipping changelog check."
  exit 0
fi