#!/bin/bash
set -e
pyflakes src/
black src/ --quiet
