#!/bin/bash
set -e
source venv/bin/activate
cd src
./manage.py test
