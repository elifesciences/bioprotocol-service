#!/bin/bash
set -e
source venv/bin/activate
pyflakes src/
black src/ --quiet
