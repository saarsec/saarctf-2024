#!/usr/bin/env bash

set -eux

SERVICENAME=$(cat servicename)
export SERVICENAME

# Build the service - the "service" directory will later be used to install.
# Can be empty if you build everything on the vulnbox. 
# You can remove files here that should never lie on the box.

apt-get update
wget -Oopenjdk.tar.gz https://download.java.net/java/GA/jdk19.0.1/afdd2e245b014143b62ccb916125e3ce/10/GPL/openjdk-19.0.1_linux-x64_bin.tar.gz
tar xvf openjdk.tar.gz
mv jdk-19.0.1 /opt/ || true
#tee /etc/profile.d/jdk19.sh << EOF
export JAVA_HOME=/opt/jdk-19.0.1
export PATH=$PATH:$JAVA_HOME/bin
#EOF
echo $JAVA_HOME
echo $PATH
java --version
cd service
cd _8BitOracle
javac -cp "SQLDriver/*" -sourcepath . src/*
cd src
jar cvfm ../../EightBitOracle.jar ../oracle.mf *.class -C ../SQLDriver/ .
mv ../SQLDriver/* ../../
cd ../..
rm -rf _8BitOracle
rm -rf ./client/src/__pycache__



# Examples:
# cd service && make -j4  # build C binary
# cd service && npm install && npm run build  # use npm to build a frontend
# rm -rf service/.gitignore service/*.iml service/.idea  # remove files that should not be on vulnbox
# rm -rf service/node_modules service/*.log service/data  # remove more things that might occur

