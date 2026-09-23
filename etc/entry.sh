#!/bin/sh
set -e
chown -R cork:cork /var/lib/cork
cd /srv/cork
if [ ! -e /var/lib/cork/sessions.json ]; then
	runuser -u cork -- sh -c "echo '{}' > /var/lib/cork/sessions.json"
fi
runuser -u cork -- .venv/bin/python bin/migrate.py apply
exec /lib/systemd/systemd
