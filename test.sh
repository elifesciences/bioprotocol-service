#!/bin/bash
set -e
source venv/bin/activate
cd src
pytest -vvv
