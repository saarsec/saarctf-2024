#!/usr/bin/env bash

set -eux

# Install the service on a fresh vulnbox. Target should be /home/<servicename>
# You get:
# - $SERVICENAME
# - $INSTALL_DIR
# - An user account with your name ($SERVICENAME)

# 1. Install dependencies (openjdk 19 binary blob)
rm -rf /opt/jdk-19.0.1
if [ -f openjdk.tar.gz ]; then
  mv openjdk.tar.gz /tmp/
else
  wget -O/tmp/openjdk.tar.gz 'https://download.java.net/java/GA/jdk19.0.1/afdd2e245b014143b62ccb916125e3ce/10/GPL/openjdk-19.0.1_linux-x64_bin.tar.gz'
fi
tar -xf /tmp/openjdk.tar.gz -C /opt/
rm -rf /tmp/openjdk.tar.gz
export JAVA_HOME=/opt/jdk-19.0.1
export PATH=$PATH:$JAVA_HOME/bin
java --version

apt-get update
apt-get install -y mariadb-server mariadb-client


# 2. TODO Copy/move files
mv service/* "$INSTALL_DIR/"
chown -R "root:$SERVICENAME" "$INSTALL_DIR"
chmod 0750 "$INSTALL_DIR"
mkdir $INSTALL_DIR/data
chown -R "$SERVICENAME:$SERVICENAME" "$INSTALL_DIR/data"
chmod 0750 "$INSTALL_DIR/data"

# 3. TODO Configure the server
# ...
# For example: 
# - adjust configs of related services (nginx/databases/...)
# - Build your service if there's source code on the box
# - ...
# 
# Useful commands:
# - nginx-location-add <<EOF
#   location {} # something you want to add to nginx default config (port 80)
#   EOF


# 4. TODO Configure startup for your service
# Typically use systemd for that:
# Install backend as systemd service
# Hint: you can use "service-add-simple '<command>' '<working directory>' '<description>'"
# service-add-simple "$INSTALL_DIR/TODO-your-script-that-should-be-started.sh" "$INSTALL_DIR/" "<TODO>"
service-add-advanced "/opt/jdk-19.0.1/bin/java -jar EightBitOracle.jar" "$INSTALL_DIR/" "8BitOracle Service" << EOF
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:/opt/jdk-19.0.1/bin
Environment=JAVA_HOME=/opt/jdk-19.0.1
EOF

# Example: Cronjob that removes stored files after a while
# cronjob-add "*/6 * * * * find $INSTALL_DIR/data -mmin +45 -type f -delete"



# 5. Startup database (CI DOCKER ONLY, not on vulnbox)
if detect-docker; then
    # docker hack for mariadb
    mkdir -p /run/mysqld
    chown mysql:mysql /run/mysqld
    /usr/sbin/mariadbd -u mysql &
    MARIADB_PID=$!
    while [ ! -e /run/mysqld/mysqld.sock ];
    do
        sleep .5 # give db time to start...
    done
fi

# 6. Create user/database
mariadb <<"EOF"
CREATE USER '8BitOracle' IDENTIFIED VIA unix_socket;
CREATE DATABASE bitoracle;
GRANT ALL ON bitoracle.* TO '8BitOracle';
EOF

# 7 Stop services (CI DOCKER ONLY)
if detect-docker; then
    kill $MARIADB_PID
fi


