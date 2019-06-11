#!/bin/bash
set -e
source venv/bin/activate
DJANGO_SETTINGS_MODULE='core.settings' pytest src/bp/tests.py -vvv
