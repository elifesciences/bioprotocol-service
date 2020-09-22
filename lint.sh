#!/bin/bash
set -e
./install.sh
source venv/bin/activate
pyflakes src/
black src/ --quiet
