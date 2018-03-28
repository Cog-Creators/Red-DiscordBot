#!/bin/bash

USER_ID=${LOCAL_USER_ID:-1000}

echo "Starting with UID : $USER_ID"
useradd --shell /bin/bash -U -u $USER_ID -o -c "" -m red
export HOME=/home/red
echo "$(id red -gn) ALL = (ALL) NOPASSWD: ALL" >> /etc/sudoers
chown -R red:red .
chmod +x ./run_red.sh
exec /usr/local/bin/gosu red "$@"