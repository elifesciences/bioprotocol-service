#!/bin/bash
set -eu

username="$1"
password="$1"

function send {
    payload="$1"
    echo "=> $payload"
    curl \
        -d "@$payload" \
        -X POST \
        -u "$username:$password" \
        -H "Content-Type: application/json" \
        -w " (HTTP %{http_code})" \
        https://ci--bp.elifesciences.org/bioprotocol/article/12345 
    echo
    echo
}

send payload.json
send partially-bad-payload.json
send bad-payload.json
send bad-data.json
