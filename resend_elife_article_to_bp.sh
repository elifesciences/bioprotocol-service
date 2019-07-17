#!/bin/bash
function is_int() { return $(test "$@" -eq "$@" > /dev/null 2>&1); }
source venv/bin/activate
set -eu
msid="$1"
if $(is_int "$msid"); then
    ./src/manage.py resend_elife_article_to_bp "$msid"
else
    echo "msid must be an integer"
    exit 1
fi
