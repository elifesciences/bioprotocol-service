#!/bin/bash
set -e
./install.sh
source venv/bin/activate
pyflakes src/
# disabled until after python3.6 -> python3.8 upgrade.
#black src/ --quiet
