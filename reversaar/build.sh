#!/usr/bin/env bash

set -eux

SERVICENAME=$(cat servicename)
export SERVICENAME

# Build the service - the "service" directory will later be used to install.
# Can be empty if you build everything on the vulnbox. 
# You can remove files here that should never lie on the box.

apt-get update
apt-get install -y libfcgi-dev libjson-c-dev zlib1g-dev uuid-dev python3-pycryptodome

pushd service/src && make clean && python3 obfuscate.py *.c *.h && make -j4 && mv reversaar.cgi .tmp.bin .. && popd && rm -rf service/src

## Patch and build fcgiwrap package
mkdir fcgiwrap
pushd fcgiwrap
# enable source repos
perl -pi -e 's/Types: deb/Types: deb deb-src/g' /etc/apt/sources.list.d/debian.sources
apt-get update
# install build-essentials
apt-get -y install build-essential

# get source
apt-get source fcgiwrap

# patch source
pushd fcgiwrap-1*
patch -u --ignore-whitespace fcgiwrap.c <<EOF
--- fcgiwrap.c.orig     2024-11-29 09:34:35.588501340 +0000
+++ fcgiwrap.c  2024-11-29 09:35:25.571990970 +0000
@@ -205,8 +205,10 @@
	if (fc->fd_stdout >= 0) close(fc->fd_stdout);
	if (fc->fd_stderr >= 0) close(fc->fd_stderr);

-       if (fc->cgi_pid)
-	       kill(SIGTERM, fc->cgi_pid);
+       if (fc->cgi_pid) {
+	       kill(fc->cgi_pid, SIGTERM);
+	       waitpid(fc->cgi_pid, NULL, 0);
+       }
 }

 static const char * fcgi_pass_fd(struct fcgi_context *fc, int *fdp, FCGI_FILE *ffp, char *buf, size_t bufsize)
@@ -350,8 +352,6 @@
		}
	}

-       fc->cgi_pid = 0;
-
	fcgi_finish(fc, "reading CGI reply (no response received)");
 }
EOF

# get build-dependencies
apt-get -y build-dep fcgiwrap

# build
dpkg-buildpackage -b

# step out, clean up
popd
mv fcgiwrap_*deb ..
popd
rm -rf fcgiwrap

# Examples:
# cd service && make -j4  # build C binary
# cd service && npm install && npm run build  # use npm to build a frontend
# rm -rf service/.gitignore service/*.iml service/.idea  # remove files that should not be on vulnbox
# rm -rf service/node_modules service/*.log service/data  # remove more things that might occur

