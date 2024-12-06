#!/usr/bin/env bash

set -eux

# Install the service on a fresh vulnbox. Target should be /home/<servicename>
# You get:
# - $SERVICENAME
# - $INSTALL_DIR
# - An user account with your name ($SERVICENAME)

# 1. Install dependencies
echo 'deb http://deb.debian.org/debian bookworm-backports main' > /etc/apt/sources.list.d/backports.list
apt-get update
apt-get install -y -t bookworm-backports golang-go

# 2. Copy/move files
mv service/* "$INSTALL_DIR/"
chown -R "root:$SERVICENAME" "$INSTALL_DIR"
chmod 0750 "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/data"
chown -R "$SERVICENAME:$SERVICENAME" "$INSTALL_DIR/data"
mkdir -p "$INSTALL_DIR/data-client"
chown -R "$SERVICENAME:$SERVICENAME" "$INSTALL_DIR/data-client"

cd $INSTALL_DIR
make

# 4. Configure startup for your service
# Typically use systemd for that:
# Install backend as systemd service
# Hint: you can use "service-add-simple '<command>' '<working directory>' '<description>'"
service-add-advanced "$INSTALL_DIR/bin/log" "$INSTALL_DIR/" "SERVICENAME log server" <<EOF
Restart=on-failure
RestartSec=10s
EOF
SERVICESUFFIX=-monitor service-add-advanced "$INSTALL_DIR/bin/monitor" "$INSTALL_DIR/" "SERVICENAME monitor server" <<EOF
After=$SERVICENAME.service
Restart=on-failure
RestartSec=10s
EOF

# Example: Cronjob that removes stored files after a while
# cronjob-add "*/6 * * * * find $INSTALL_DIR/data -mmin +45 -type f -delete"



# Example: Initialize Databases (PostgreSQL example)

# Example: 5. Startup database (CI DOCKER ONLY, not on vulnbox)
# if detect-docker; then
#     EXAMPLE for PostgreSQL: pg_ctlcluster 11 main start
# fi

# Example: 6. Configure PostgreSQL
# cp $INSTALL_DIR/*.sql /tmp/
# sudo -u postgres psql -v ON_ERROR_STOP=1 -f "/tmp/init.sql"

# Example: 7 Stop services (CI DOCKER ONLY)
# if detect-docker; then
#     pg_ctlcluster 11 main stop
# fi
