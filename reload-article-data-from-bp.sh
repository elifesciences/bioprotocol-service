#!/bin/bash
function is_int() { return $(test "$@" -eq "$@" > /dev/null 2>&1); }
source venv/bin/activate
set -eu
msid="$1"
if $(is_int "$msid"); then
    ./src/manage.py reload_article_data "$msid"
else
    echo "msid must be an integer"
    exit 1
fi
