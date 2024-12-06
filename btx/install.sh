#!/usr/bin/env bash

set -eux

# Install the service on a fresh vulnbox. Target should be /home/<servicename>
# You get:
# - $SERVICENAME
# - $INSTALL_DIR
# - An user account with your name ($SERVICENAME)

# 1. TODO Install dependencies
# EXAMPLE: apt-get install -y nginx
apt-get update
apt-get install -y socat

# 2. TODO Copy/move files
pwd
ls
mv service/* "$INSTALL_DIR/"
mkdir -p "$INSTALL_DIR/bildschirmtext/messages"
chown -R "root:$SERVICENAME" "$INSTALL_DIR"  # service code: read-only
chown -R "$SERVICENAME:$SERVICENAME" "$INSTALL_DIR/bildschirmtext/blogs"  # service data: read-write
chown -R "$SERVICENAME:$SERVICENAME" "$INSTALL_DIR/bildschirmtext/data"  # service data: read-write
chown -R "$SERVICENAME:$SERVICENAME" "$INSTALL_DIR/bildschirmtext/secrets"  # service data: read-write
chown -R "$SERVICENAME:$SERVICENAME" "$INSTALL_DIR/bildschirmtext/stats"  # service data: read-write
chown -R "$SERVICENAME:$SERVICENAME" "$INSTALL_DIR/bildschirmtext/users"  # service data: read-write
chown -R "$SERVICENAME:$SERVICENAME" "$INSTALL_DIR/bildschirmtext/messages"  # service data: read-write
chown "root:$SERVICENAME" "$INSTALL_DIR/bildschirmtext/secrets/0-1.secrets"
chown "root:$SERVICENAME" "$INSTALL_DIR/bildschirmtext/users/0-1.user"

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
service-add-simple "socat -s -T300 TCP-LISTEN:1983,fork,reuseaddr EXEC:'python3 -u neu-ulm.py',setsid,stdout" "$INSTALL_DIR/bildschirmtext/server" "run btx"

# Example: Cronjob that removes stored files after a while
cronjob-add "*/6 * * * * find $INSTALL_DIR/bildschirmtext/blogs -mmin +45 -type f -delete"
cronjob-add "*/6 * * * * find $INSTALL_DIR/bildschirmtext/stats -mmin +45 -type f -delete"
cronjob-add "*/6 * * * * find $INSTALL_DIR/bildschirmtext/secrets -mmin +45 -type f ! -name '0-1.secrets' -delete"
cronjob-add "*/6 * * * * find $INSTALL_DIR/bildschirmtext/users -mmin +45 -type f ! -name '0-1.user' -delete"



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
