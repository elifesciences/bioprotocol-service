#!/bin/bash
set -e
. mkvenv.sh
source venv/bin/activate

echo "installing ..."
pip install -r requirements.txt

if [ ! -e app.cfg ]; then
    ln -s elife.cfg app.cfg
fi

echo "installing/updating database ..."
./src/manage.py migrate --no-input
