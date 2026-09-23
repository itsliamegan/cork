#!/bin/sh
chown -R cork:cork /var/lib/cork
exec /lib/systemd/systemd
