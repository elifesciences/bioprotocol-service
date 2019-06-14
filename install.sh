#!/bin/bash
set -e
. mkvenv.sh
source venv/bin/activate

echo "installing ..."
if [ -e requirements.lock ]; then
    # remove the .lock file when you want to recreate it
    pip install -r requirements.lock
else
    pip install -r requirements.txt
    echo "locking..."
    pip freeze > requirements.lock
    echo "wrote 'requirements.lock'"
fi

if [ ! -e app.cfg ]; then
    ln -s elife.cfg app.cfg
fi
