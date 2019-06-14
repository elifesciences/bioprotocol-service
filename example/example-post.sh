#!/bin/bash
set -eu

function send {
    payload="$1"
    echo "=> $payload"
    curl \
        -d "@$payload" \
        -X POST \
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
