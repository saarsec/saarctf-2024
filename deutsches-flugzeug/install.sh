#!/usr/bin/env bash

set -eux

# Install the service on a fresh vulnbox. Target should be /home/<servicename>
# You get:
# - $SERVICENAME
# - $INSTALL_DIR
# - An user account with your name ($SERVICENAME)

# 1. Install dependencies
# EXAMPLE: apt-get install -y nginx
apt-get update
apt install -y python3 python3-pip python3-virtualenv python3-venv ghostscript


# 2. Copy/move files
mv service/* "$INSTALL_DIR/"
chown -R "root:$SERVICENAME" "$INSTALL_DIR"
chmod 0750 "$INSTALL_DIR"
mkdir -p "$INSTALL_DIR/data"
chown $SERVICENAME:$SERVICENAME "$INSTALL_DIR/data"
chmod 0750 "$INSTALL_DIR/data"

# 3. venv
python3 -m venv $INSTALL_DIR/venv
. $INSTALL_DIR/venv/bin/activate
pip install flask python-jwt==3.0 jwcrypto treepoem ghostscript pyopenssl gunicorn


# 4. Configure startup for your service
# Typically use systemd for that:
# Install backend as systemd service
# Hint: you can use "service-add-simple '<command>' '<working directory>' '<description>'"
# service-add-simple "$INSTALL_DIR/your-script-that-should-be-started.sh" "$INSTALL_DIR/" "<>"
service-add-simple "$INSTALL_DIR/venv/bin/python wsgi.py" "$INSTALL_DIR" "Deutsches Flugzeug saarCTF 2024"

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
