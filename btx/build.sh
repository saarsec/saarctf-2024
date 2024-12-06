#!/usr/bin/env bash

set -eux

SERVICENAME=$(cat servicename)
export SERVICENAME
# empty

find -type f -name '.gitkeep' -delete
