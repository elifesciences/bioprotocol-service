#!/bin/bash
set -eux

function hit {
    path="$1"
    test $(curl --write-out %{http_code} --silent --output /dev/null https://$(hostname)$path) = 200
}

hit /ping
hit /status
