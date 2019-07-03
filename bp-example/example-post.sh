#!/bin/bash
# sends a dummy POST to the BioProtocol test server

set -eu

function send {
    payload="$1"
    echo "=> $payload"
    curl \
        --silent \
        --output /dev/null \
        -d "@$payload" \
        -X POST \
        -H "Content-Type: application/json" \
        -w " (HTTP %{http_code})" \
        https://dev.bio-protocol.org/api/elife00003?action=sendArticle 
    echo
    echo
}

send payload.json
send partially-bad-payload.json
send bad-payload.json
send bad-data.json
