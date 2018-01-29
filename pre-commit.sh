#!/bin/bash
set -e
./code-check.sh
python3 setup.py test
