# Deployment

Cork runs on a single VPS behind nginx, served by gunicorn under systemd. The
unit files live in `etc/` and are copied to `/etc/systemd/system/` on the
server. This note covers the intended layout, the migration from the original
`/home/web` install, and the one systemd behaviour that made the original
configuration work by accident.

## Layout

The VPS is expected to host more than one application, so each app gets its own
system user and its own directory under `/srv`:

```
/srv/cork        web:web, 0755     (data/ is cork:cork, 0750)
/srv/helios      web:web, 0755
/srv/luna        web:web, 0755
```

`web` is the login account used to deploy. `cork` is a `nologin` service
account that runs the units and owns nothing but `data/`. Keeping them separate
means a compromise of the application reaches neither the deploying user's SSH
keys nor the code the application will execute after the next restart. Each
additional application gets its own service user on the same pattern.

Helios and Luna are declared in `pyproject.toml` as editable path dependencies
at `../helios` and `../luna`, so they must stay siblings of the application
directory. Keeping them at `/srv` means a second application placed at
`/srv/<app>` resolves the same paths with no per-app configuration.

They are owned by the deploying user, never by a service user. Both
applications import Helios, so write access from one application's service user
would turn a compromise of that application into a compromise of the other.
Nothing writes them at runtime: `uv sync` records the editable install in the
venv rather than the source tree, and `ProtectSystem=strict` makes the tree
read-only inside each unit's namespace in any case.

`uv` belongs at `/usr/local/bin/uv`. `ProtectHome=yes` makes anything under a
home directory unreachable to the units.

## Units

- `etc/cork.socket` — systemd owns `/run/cork.sock` and passes it to gunicorn.
  `SocketUser=www-data` is what lets nginx connect. Enable this one, not
  `cork.service`; the socket activates the service.
- `etc/cork.service` — gunicorn via `/srv/cork/.venv/bin/gunicorn`, logging to
  stdout so journald captures it (`journalctl -u cork`).
- `etc/cork-backup.service` + `etc/cork-backup.timer` — daily R2 backup, run
  via `/srv/cork/.venv/bin/python` so no `uv` is needed at runtime. Its R2
  credentials come from `EnvironmentFile=/etc/cork/backup.env`, which is not in
  the repository — see [Secrets](#secrets).

Both services run one venv, built by:

```
uv sync --no-default-groups --group backup
```

That resolves the project dependencies (gunicorn, helios) plus the `backup`
group (cloudflare, luna), and omits the `dev` group.

Because gunicorn takes its listening socket from systemd, `--bind` in
`ExecStart` would be ignored: the arbiter checks `LISTEN_FDS` first and uses
the inherited descriptors. Under `ProtectSystem=strict` it could not create a
socket in `/run` on its own anyway.

### Secrets

The two environment files are read by different things, which is what decides
where each one lives.

`/etc/cork/backup.env` holds the R2 credentials (`etc/backup.env.example` lists
the keys). systemd reads `EnvironmentFile=` as PID 1, before it builds the
unit's mount namespace and before it drops to `User=cork`, so the path is
unaffected by `ProtectSystem=strict` and `ProtectHome=yes`, and the service user
never needs to read the file at all. That allows the tightest ownership
available, `root:root` and `0600`, and keeps the credentials outside the
worktree where no `git add` can reach them and a re-clone of `/srv/cork` cannot
lose them.

`/srv/cork/.env` holds the application configuration and cannot move: it is read
by the application itself, not by systemd, and `app/config.py` resolves it as
`ROOT_DIR/.env`. It stays `web:cork` and `0640` — `web` writes it, `cork` reads
it as the running process.

Changing `/etc/cork/backup.env` needs no `daemon-reload`; systemd re-reads an
`EnvironmentFile=` on every start of the unit.

### ReadWritePaths is load-bearing

`ProtectSystem=strict` mounts the whole filesystem read-only. Cork's store is
JSON files rewritten in place — including a temporary file written into the
same directory before `os.replace` — and the persistence lock is opened for
writing, so both units declare:

```
ReadWritePaths=/srv/cork/data
```

Any second application under `/srv` needs its own equivalent.

### Why the original /home install worked without it

The original unit had `ProtectSystem=strict` with `ReadWritePaths` naming only
the log directory, and writes still succeeded. Inspecting the running process
explained it:

```
/dev/vda1 /      ext4 ro,...
/dev/vda1 /home  ext4 rw,...
```

When `ProtectHome=` is off (the default), systemd adds `/home`, `/root` and
`/run/user` back as writable so that `ProtectSystem=strict` does not silently
make home directories read-only — `ProtectHome=` is meant to be the only
setting governing those paths. `man systemd.exec` documents the analogous
carve-out for `PrivateTmp=` but not this one.

The application therefore depended on an undocumented interaction plus the
happenstance of being installed under `/home`. `/srv` gets no such exemption,
which is why the explicit `ReadWritePaths` matters after the move.

## Deploying

Log in as `web` and pull each repository, then sync and restart:

```
cd /srv/helios && git pull
cd /srv/luna   && git pull
cd /srv/cork   && git pull

uv sync --no-default-groups --group backup
sudo systemctl restart cork.service
```

All three projects are installed into the venv as editable `.pth` entries
pointing at their source directories, so a pull is enough to update the code
itself. `uv sync` is only strictly needed when `uv.lock` changed, but it is
fast and idempotent when nothing has, so it is simpler to run it every time
than to decide.

### Restart permission

`web` has no sudo rights, which is deliberate: giving the deploy account
general sudo would undo the separation above, since anyone reaching that
account could then become root. It needs exactly one privileged command, so
grant that one and nothing else. As the sudo user, once:

```
sudo visudo -f /etc/sudoers.d/cork-deploy
```

```
web ALL=(root) NOPASSWD: /usr/bin/systemctl restart cork.service
```

`visudo` validates the syntax before saving; a malformed sudoers file can lock
everyone out of sudo. The rule matches that exact command only — no other unit,
and no other systemctl verb.

Because gunicorn is socket-activated, systemd holds the listening socket across
the restart and queues incoming connections rather than refusing them, so a
deploy drops no requests.

Two steps are *not* part of a normal deploy. Both need broader privileges than
the rule above, so run them as the sudo user:

- **nginx** only needs `sudo nginx -t && sudo systemctl reload nginx` when the
  nginx configuration itself changed. Application deploys do not touch it.
- **`daemon-reload`** only applies when a unit file in `etc/` changed:

  ```
  sudo cp /srv/cork/etc/cork.{service,socket} /srv/cork/etc/cork-backup.{service,timer} /etc/systemd/system/
  sudo systemctl daemon-reload
  sudo systemctl restart cork.socket cork.service
  ```

  Editing the copies in `/etc/systemd/system/` directly puts the server out of
  step with the repository; change `etc/` and copy.

Then confirm:

```
systemctl status cork.service --no-pager
journalctl -u cork -n 20 --no-pager
```

## Migration from /home/web/cork

Downtime is acceptable. A virtualenv cannot be relocated — `pyvenv.cfg` and
every script shebang hard-code absolute paths, and the editable `.pth` entries
record the old Helios, Luna and Cork locations — so the venv is rebuilt rather
than copied.

Run every step as the sudo user except step 5, which runs as `web`.

Check `/srv/cork/.env` for absolute `/home/web/...` paths in the `APP_*` values
before starting. The R2 credentials have no file yet — the backup has only ever
been run `--dry` — so step 4 creates `/etc/cork/backup.env` from scratch. Check
`/srv/cork/.env` and the old install's shell environment first in case the four
`APP_BACKUP_*` / `CLOUDFLARE_*` values are already recorded somewhere.

1. Install uv system-wide:

   ```
   curl -LsSf https://astral.sh/uv/install.sh | sudo env UV_INSTALL_DIR=/usr/local/bin sh
   ```

2. Stop the old service. Do this before copying, or the copied `store.json`
   will be older than the last request served:

   ```
   sudo systemctl disable --now gunicorn.service gunicorn.socket
   ```

3. Copy rather than move, so the original stays as a rollback:

   ```
   sudo mkdir -p /srv
   sudo rsync -a /home/web/cork/ /srv/cork/
   sudo rsync -a /home/web/helios/ /srv/helios/
   sudo rsync -a /home/web/luna/ /srv/luna/
   sudo rm -rf /srv/cork/.venv
   ```

4. Create the service account and set ownership. `web` keeps the code so the
   application cannot rewrite what it executes; `cork` owns only `data/`:

   ```
   sudo useradd --system --no-create-home --shell /usr/sbin/nologin cork
   sudo chown -R web:web /srv/cork /srv/helios /srv/luna
   sudo chown -R cork:cork /srv/cork/data
   sudo chmod 755 /srv/cork
   sudo chmod 750 /srv/cork/data
   sudo chown web:cork /srv/cork/.env
   sudo chmod 640 /srv/cork/.env
   ```

   Then create the R2 credentials file the backup unit expects. There is no
   existing one to move, so it starts as a copy of the example:

   ```
   sudo install -d -m 0755 /etc/cork
   sudo install -m 0600 -o root -g root /srv/cork/etc/backup.env.example /etc/cork/backup.env
   sudo -e /etc/cork/backup.env
   ```

   Fill in all four values. `APP_BACKUP_PREFIX` already has a usable default of
   `backups`; the other three come from the R2 bucket and an API token scoped to
   it, created in the Cloudflare dashboard. `sudo -e` edits a temporary copy as
   the invoking user and writes it back as root, so the permissions set by
   `install` survive the edit.

   `/srv/cork` stays world-readable because nginx serves `public/static` as
   `www-data`. `data/` does not: `sessions.json` is session state.
   `/etc/cork/backup.env` can be `root:root` because systemd reads it as PID 1;
   see [Secrets](#secrets).

5. Rebuild the venv as `web`. This is also what re-points the editable installs
   at `/srv`:

   ```
   cd /srv/cork && uv sync --no-default-groups --group backup
   .venv/bin/python -c "import helios, luna; print(helios.__file__)"
   ```

   The second command should print a path under `/srv`. `cork` needs only read
   and execute on the venv, which the `0755` directories provide.

6. Install the units. `/etc/cork/backup.env` must already be in place from
   step 4, or the first backup runs without its credentials:

   ```
   sudo cp /srv/cork/etc/cork.{service,socket} /srv/cork/etc/cork-backup.{service,timer} /etc/systemd/system/
   sudo systemctl daemon-reload
   sudo systemctl enable --now cork.socket cork-backup.timer
   ```

7. Point nginx at `proxy_pass http://unix:/run/cork.sock;`, then
   `sudo nginx -t && sudo systemctl reload nginx`.

### Verification

```
curl --unix-socket /run/cork.sock http://localhost/
journalctl -u cork -n 50 --no-pager
```

Then create a board through the site. Writes are the thing the original setup
never exercised under `strict`; a wrong `ReadWritePaths` shows up as a
`PersistenceError` in the journal straight away.

Confirm the sandbox has no writable `/home` bind mount this time:

```
grep -E ' / | /home' /proc/$(systemctl show -p MainPID --value cork.service)/mounts
```

Then run the backup once by hand. Every test so far has been `--dry`, so this
is the first real upload and where a wrong token or bucket name surfaces:

```
sudo systemctl start cork-backup.service
journalctl -u cork-backup -n 20 --no-pager
systemctl list-timers cork-backup.timer
```

### Rollback

`/home/web/cork` is untouched: re-enable the old units, revert the nginx
`proxy_pass`, reload nginx. Remove the old copies and the `web` user's
application directories once the new install has been running happily.
