#!/bin/sh
# Connect to a rooted Xiaomi router over SSH.
#
# The stock firmware ships dropbear 2017.75, which only offers the SHA-1 "ssh-rsa"
# host key. OpenSSH 8.8+ disables that algorithm by default, so both flags below are
# mandatory - without them you get "no matching host key type found. Their offer: ssh-rsa".
#
# Usage:
#   sh scripts/ssh-xiaomi.sh                  # default 192.168.31.1
#   sh scripts/ssh-xiaomi.sh 10.0.0.1         # custom address (e.g. after changing the LAN subnet)
#   sh scripts/ssh-xiaomi.sh 192.168.31.1 id  # run a single command and exit

set -eu

HOST="${1:-192.168.31.1}"
shift 2>/dev/null || true

exec ssh \
    -o HostKeyAlgorithms=+ssh-rsa \
    -o PubkeyAcceptedAlgorithms=+ssh-rsa \
    -o StrictHostKeyChecking=no \
    -o UserKnownHostsFile=/dev/null \
    -o LogLevel=ERROR \
    "root@${HOST}" "$@"
