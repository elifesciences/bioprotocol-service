#!/bin/bash
set -e
./install.sh
source venv/bin/activate
pip install -r requirements-dev.txt
cd src
pytest -vvv
