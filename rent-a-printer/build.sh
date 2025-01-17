#!/usr/bin/env bash

set -eux

SERVICENAME=$(cat servicename)
export SERVICENAME

# Build the service - the "service" directory will later be used to install.
# Can be empty if you build everything on the vulnbox. 
# You can remove files here that should never lie on the box.

# Examples:
# cd service && make -j4  # build C binary
# cd service && npm install && npm run build  # use npm to build a frontend
# rm -rf service/.gitignore service/*.iml service/.idea  # remove files that should not be on vulnbox
# rm -rf service/node_modules service/*.log service/data  # remove more things that might occur


cd service
rm -rf data demo tests __pycache__

find . -type d -iname __pycache__ -exec rm -rf \;

sed -i '/REMOVE-VULNBOX/d' 'management/add_printer.py'
sed -i '/REMOVE-VULNBOX/d' 'printer_utils.py'

# really?
rm -f requirements-dev.txt pyproject.toml
