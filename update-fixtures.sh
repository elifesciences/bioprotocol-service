#!/bin/bash
set -e
curl https://prod--gateway.elifesciences.org/articles/3/versions/1 | jq . > src/bp/tests/fixtures/elife-00003-v1.xml.json
