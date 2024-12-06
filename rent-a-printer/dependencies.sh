#!/usr/bin/env bash

set -eux

# Install all your checkerscript / exploit dependencies
# Please prefer Debian packages over pip (for stability reasons)
# OS will be Debian Bullseye.
# Already installed python modules are:
# - redis
# - requests
# - pwntools
# - numpy
# - pycryptodome
# - psutil
# - bs4
# - pytz

# uncomment for APT
apt-get update
apt-get install -y fonts-roboto-unhinted libzbar0

# checkers
python3 -m pip install fpdf pyipp opencv-python-headless pypdf[image] pyzbar
# exploits
python3 -m pip install flask flask-login
