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
# apt update
# apt install -y python3-requests
cd /opt
rm -rf /opt/jdk-19.0.1
rm -rf openjdk-19.0.1_linux-x64_bin.tar.gz
wget https://download.java.net/java/GA/jdk19.0.1/afdd2e245b014143b62ccb916125e3ce/10/GPL/openjdk-19.0.1_linux-x64_bin.tar.gz
tar xvf openjdk-19.0.1_linux-x64_bin.tar.gz
export JAVA_HOME=/opt/jdk-19.0.1
export PATH=$PATH:$JAVA_HOME/bin

# uncommnent for pip
# python3 -m pip install requests
