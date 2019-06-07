#!/bin/bash
set -e
. mkvenv.sh
source venv/bin/activate
pip install -r requirements.lock
if [ ! -e app.cfg ]; then
    ln -s elife.cfg app.cfg
fi
