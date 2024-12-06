#!/usr/bin/env bash

set -eux

# Install the service on a fresh vulnbox. Target should be /home/<servicename>
# You get:
# - $SERVICENAME
# - $INSTALL_DIR
# - An user account with your name ($SERVICENAME)


# For now: use archive repo to get old versions. Not sure if the pin works as expected.
mv /etc/apt/sources.list /etc/apt/sources.list.d/stable.list || true
ls -l /etc/apt/sources.list.d
# echo 'deb     [check-valid-until=no] https://snapshot.debian.org/archive/debian/20240924T203152Z/ bookworm main' > /etc/apt/sources.list.d/legacy.list
echo 'deb     [check-valid-until=no] http://HTTPS///snapshot.debian.org/archive/debian/20240924T203152Z/ bookworm main' > /etc/apt/sources.list.d/legacy.list
#echo 'Package: *'             >  /etc/apt/preferences.d/stable.pref
#echo 'Pin: release a=stable'  >> /etc/apt/preferences.d/stable.pref
#echo 'Pin-Priority: 500'      >> /etc/apt/preferences.d/stable.pref
#echo 'Package: *'             >  /etc/apt/preferences.d/legacy.pref
#echo 'Pin: release a=legacy'  >> /etc/apt/preferences.d/legacy.pref
#echo 'Pin-Priority: 1'        >> /etc/apt/preferences.d/legacy.pref

# pin packages, so that apt upgrade won't touch them
cat - <<'EOF' > /etc/apt/preferences.d/cups.pref
Package: cups
Pin: version 2.4.2-3+deb12u7
Pin-Priority: 999

Package: libcups2
Pin: version 2.4.2-3+deb12u7
Pin-Priority: 999

Package: libcupsimage2
Pin: version 2.4.2-3+deb12u7
Pin-Priority: 999

Package: libcups2-dev
Pin: version 2.4.2-3+deb12u7
Pin-Priority: 999

Package: libcupsimage2-dev
Pin: version 2.4.2-3+deb12u7
Pin-Priority: 999

Package: cups-client
Pin: version 2.4.2-3+deb12u7
Pin-Priority: 999

Package: cups-core-drivers
Pin: version 2.4.2-3+deb12u7
Pin-Priority: 999

Package: cups-daemon
Pin: version 2.4.2-3+deb12u7
Pin-Priority: 999

Package: cups-ipp-utils
Pin: version 2.4.2-3+deb12u7
Pin-Priority: 999

Package: cups-server-common
Pin: version 2.4.2-3+deb12u7
Pin-Priority: 999

Package: cups-common
Pin: version 2.4.2-3+deb12u7
Pin-Priority: 999

Package: cups-ppdc
Pin: version 2.4.2-3+deb12u7
Pin-Priority: 999

Package: cups-filters-core-drivers
Pin: version 1.28.17-3
Pin-Priority: 999

Package: cups-browsed
Pin: version 1.28.17-3
Pin-Priority: 999

Package: cups-filters
Pin: version 1.28.17-3
Pin-Priority: 999

Package: libcupsfilters1
Pin: version 1.28.17-3
Pin-Priority: 999

Package: libcupsfilters-dev
Pin: version 1.28.17-3
Pin-Priority: 999
EOF

# 1. Install dependencies
apt-get update

# cups / potential candidate dependencies for downgrade / recommended packages
# cups 2.4.2-3+deb12u7 is likely what we want for now
apt-get install -y --allow-downgrades \
		cups=2.4.2-3+deb12u7 \
		libcups2=2.4.2-3+deb12u7 \
		libcupsimage2=2.4.2-3+deb12u7 \
		libcups2-dev=2.4.2-3+deb12u7 \
		libcupsimage2-dev=2.4.2-3+deb12u7 \
		cups-client=2.4.2-3+deb12u7 \
		cups-core-drivers=2.4.2-3+deb12u7 \
		cups-daemon=2.4.2-3+deb12u7 \
		cups-ipp-utils=2.4.2-3+deb12u7 \
		cups-server-common=2.4.2-3+deb12u7 \
		cups-common=2.4.2-3+deb12u7 \
		cups-filters-core-drivers=1.28.17-3 \
		cups-browsed=1.28.17-3 \
		cups-filters=1.28.17-3 \
		libcupsfilters1=1.28.17-3 \
		libcupsfilters-dev=1.28.17-3 \
		cups-ppdc=2.4.2-3+deb12u7 \
		lpr
apt-get install -y avahi-daemon avahi-autoipd printer-driver-cups-pdf cups-pdf
apt-get install -y net-tools
apt-get install -y python3 python3-pip python3-virtualenv python3-venv build-essential graphicsmagick-imagemagick-compat

# remove snapshot repo again
rm /etc/apt/sources.list.d/legacy.list


# enable logging in cups-browsed
echo 'DebugLogging file stderr' >> /etc/cups/cups-browsed.conf

# enable the udp:631 port (apparently disabled by default)
sed -i 's|^BrowseRemoteProtocols .*|BrowseRemoteProtocols dnssd cups|' /etc/cups/cups-browsed.conf

# Enable management interface / printer sharing / logging. Config file after:
# cupsctl --remote-any --share-printers --debug-logging
cp service/cupsd.conf /etc/cups/cupsd.conf
rm service/cupsd.conf

# cups-browsed should not be too easy to stop
echo 'WantedBy=cups.service' >> /lib/systemd/system/cups-browsed.service
systemctl enable cups-browsed || true  # fails in docker

# harden filters
rm -f /usr/lib/cups/filter/foomatic-rip /usr/lib/cups/filter/cupsomatic
touch /usr/lib/cups/filter/foomatic-rip
chmod 0600 /usr/lib/cups/filter/foomatic-rip
chattr +i /usr/lib/cups/filter/foomatic-rip || true  # fails in docker

# enable imagemagick pdf conversion
# not sure if necessary with graphicsmagick
sed -i 's|<policy domain="coder" rights="none" pattern="PDF" />|<policy domain="coder" rights="read" pattern="PDF" />|' /etc/ImageMagick-6/policy.xml || true


# 2. Copy/move files
mv service/* "$INSTALL_DIR/"
mkdir -p "$INSTALL_DIR/data"
chown -R "root:$SERVICENAME" "$INSTALL_DIR"  # service code: read-only
chmod 0750 $INSTALL_DIR
# service data: rw for python, ro for cups
chown -R "$SERVICENAME:$SERVICENAME" "$INSTALL_DIR/data"
chmod 0750 "$INSTALL_DIR/data"

# CUPS and filters should be able to read all data files
usermod -a -G $SERVICENAME lp
# cups filters should run with group "$SERVICENAME"
sed -i "s|^#Group .*|Group $SERVICENAME|" /etc/cups/cups-files.conf

# CUPS admin account for management scripts
useradd $SERVICENAME-admin
usermod -aG $SERVICENAME $SERVICENAME-admin
usermod -aG lp $SERVICENAME-admin
usermod -aG lpadmin $SERVICENAME-admin

# allow management scripts as admin (with sudo)
echo "$SERVICENAME ALL=($SERVICENAME-admin) NOPASSWD: $INSTALL_DIR/venv/bin/python $INSTALL_DIR/management/add_printer.py *" > /etc/sudoers.d/$SERVICENAME
echo "$SERVICENAME ALL=($SERVICENAME-admin) NOPASSWD: $INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/management/add_printer.py *" >> /etc/sudoers.d/$SERVICENAME
echo "$SERVICENAME ALL=($SERVICENAME-admin) NOPASSWD: $INSTALL_DIR/venv/bin/python $INSTALL_DIR/management/cleanup_expired_printers.py" >> /etc/sudoers.d/$SERVICENAME
echo "$SERVICENAME ALL=($SERVICENAME-admin) NOPASSWD: $INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/management/cleanup_expired_printers.py" >> /etc/sudoers.d/$SERVICENAME


# 3. Create venv
python3 -m venv $INSTALL_DIR/venv
. $INSTALL_DIR/venv/bin/activate
pip install -r $INSTALL_DIR/requirements.txt

# install filters
echo -e "#!/bin/sh\ncd $INSTALL_DIR\nexport PYTHONPATH=$INSTALL_DIR\nexec ${INSTALL_DIR}/venv/bin/python ${INSTALL_DIR}/filters/add_template.py" '"$@"' > /usr/lib/cups/filter/add_template.py
echo -e "#!/bin/sh\ncd $INSTALL_DIR\nexport PYTHONPATH=$INSTALL_DIR\nexec ${INSTALL_DIR}/venv/bin/python ${INSTALL_DIR}/filters/qrcodes.py" '"$@"' > /usr/lib/cups/filter/qrcodes.py
chmod +x /usr/lib/cups/filter/*.py

# init database, set permissions to 0640, init some printers
if ! detect-docker; then
  sudo -u "$SERVICENAME" $INSTALL_DIR/venv/bin/python3 "$INSTALL_DIR/init_db.py"
fi
rm "$INSTALL_DIR/init_db.py"
chgrp $SERVICENAME-admin $INSTALL_DIR/data/db.sqlite3 || true

# 4. Configure startup for your service
# service-add-simple "$INSTALL_DIR/venv/bin/python app.py" "$INSTALL_DIR" "Rent-a-printer web interface"
service-add-simple "$INSTALL_DIR/venv/bin/gunicorn -b 0.0.0.0:6310 -w 1 --threads 4 'app:default_app()'" "$INSTALL_DIR" "Rent-a-printer web interface"
# TODO harden against potential RCE in lp/cups

# add cronjob for cleanup
SERVICENAME=$SERVICENAME-admin \
  cronjob-add "0,30 * * * * $INSTALL_DIR/venv/bin/python $INSTALL_DIR/management/cleanup_expired_printers.py"



# docker patches - so cups socket available
if detect-docker; then
  echo 'root:123456789' | chpasswd
  sed -i '/return cups.Connection/i \ \ \ \ cups.setUser("root")' $INSTALL_DIR/management/add_printer.py
  sed -i '/return cups.Connection/i \ \ \ \ cups.setPasswordCB(lambda _: "123456789")' $INSTALL_DIR/management/add_printer.py
  sed -i '/return cups.Connection/i \ \ \ \ return cups.Connection(host="127.0.0.1")' $INSTALL_DIR/management/add_printer.py
fi


# remove later
#curl -o /usr/local/bin/rmate https://raw.githubusercontent.com/aurora/rmate/master/rmate || true
#sudo chmod +x /usr/local/bin/rmate || true
#apt-get install -y silversearcher-ag
