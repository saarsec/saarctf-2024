#!/usr/bin/env bash

set -eux

export PORT=7331

# Install the service on a fresh vulnbox. Target should be /home/<servicename>
# You get:
# - $SERVICENAME
# - $INSTALL_DIR
# - An user account with your name ($SERVICENAME)

# 1. Install dependencies
# EXAMPLE: apt-get install -y nginx
apt-get update
apt-get install -y nginx spawn-fcgi fcgiwrap libfcgi-bin libjson-c5 multiwatch zlib1g libuuid1

# 1.5 Install patched package
dpkg -i fcgiwrap_*deb && rm fcgiwrap_*deb

# 2. Copy/move files
mv service/{.*,*} "$INSTALL_DIR/"
mkdir -p "$INSTALL_DIR/data/users" "$INSTALL_DIR/data/files"
chown -R "root:$SERVICENAME" "$INSTALL_DIR"  # service code: read-only
chmod a+x "$INSTALL_DIR" # needed so that nginx can access the /web subdirectory...
chown -R "$SERVICENAME:www-data" "$INSTALL_DIR/data"  # service data: read-write
chown -R "$SERVICENAME:www-data" "$INSTALL_DIR/web"  # service data: read-write

# 3. Configure the server
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
##
# IMPORTANT: "SCRIPT_FILENAME" must be set _BEFORE_ including fastcgi.conf, it _cannot_ be overwritten later!
#
cat - > /etc/nginx/sites-available/$SERVICENAME <<EOF
server {
    listen $PORT;
    root $INSTALL_DIR/web;
    location /api {
        fastcgi_param SCRIPT_FILENAME $INSTALL_DIR/reversaar.cgi;
        include fastcgi.conf;
        fastcgi_pass unix:/tmp/$SERVICENAME.sock;
    }
    location /userdata {
        alias $INSTALL_DIR/data/files/;
        sendfile   on;
        tcp_nopush on;
    }
}
EOF
ln -s /etc/nginx/sites-available/$SERVICENAME /etc/nginx/sites-enabled/$SERVICENAME


# 4. TODO Configure startup for your service
# Typically use systemd for that:
# Install backend as systemd service
# Hint: you can use "service-add-simple '<command>' '<working directory>' '<description>'"
# service-add-simple "$INSTALL_DIR/TODO-your-script-that-should-be-started.sh" "$INSTALL_DIR/" "<TODO>"
service-add-simple "spawn-fcgi -n -s /tmp/$SERVICENAME.sock -M 666 -- $(which multiwatch) -f 64 -- $(which fcgiwrap) -f -p $INSTALL_DIR/reversaar.cgi" "$INSTALL_DIR" "$SERVICENAME"

# Example: Cronjob that removes stored files after a while
cronjob-add "*/6 * * * * find $INSTALL_DIR/data/files -mmin +45 -type f -delete"



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
