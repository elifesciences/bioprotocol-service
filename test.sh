#!/bin/bash
set -e
./install.sh
source venv/bin/activate
cd src
pytest -vvv
