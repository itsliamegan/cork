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
/srv/cork        web:web, 0755
/srv/helios      web:web, 0755
/srv/luna        web:web, 0755
/var/lib/cork    cork:cork, 0750   (the database and sessions)
```

`web` is the login account used to deploy. `cork` is a `nologin` service
account that runs the units and owns nothing but `/var/lib/cork`. Keeping them separate
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

- `etc/cork.socket` — systemd owns the socket and passes it to gunicorn.
  Production listens on `/run/cork.sock`; the unit in the repository uses
  `/run/cork/cork.sock` for the development container.
  `SocketUser=www-data` is what lets nginx connect. Enable this one, not
  `cork.service`; the socket activates the service.
- `etc/cork.service` — gunicorn via `/srv/cork/.venv/bin/gunicorn`, logging to
  stdout so journald captures it (`journalctl -u cork`). `--preload` imports
  Cork in the main process before forking workers, so an import error fails
  `systemctl start` instead of the first request. It also means a `reload`
  (HUP) does not pick up new code; deploys stop and start the service.
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

`ProtectSystem=strict` mounts the whole filesystem read-only. Cork writes to
`/var/lib/cork`: the SQLite database and the rollback journal SQLite creates beside it
during each write, `sessions.json` — rewritten through a temporary file in the
same directory before `os.replace` — and the session lock, which is opened for
writing. `cork.service` therefore declares:

```
ReadWritePaths=/var/lib/cork
```

`cork-backup.service` declares the same path but only reads the database. It
opens it read-only and copies it with SQLite's backup API into its private
`/tmp`. A read-only connection
cannot roll back a hot journal left by a crashed write, so if the backup fails
with a read-only error after a crash, start Cork once to recover the journal.

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

## Data files

`/var/lib/cork` holds `store.sqlite` (the database), `sessions.json`, and
`sessions.lock`. These are the defaults in `app/config.py`, so `.env` needs no
`APP_DATABASE_FILE`, `APP_SESSION_STORE_FILE`, or `APP_SESSION_LOCK_FILE`
unless a path differs. A fresh
environment needs the first two before Cork starts, because neither is created
on demand:

```
sudo -u cork sh -c "echo '{}' > /var/lib/cork/sessions.json"
sudo -u cork /srv/cork/.venv/bin/python bin/migrate.py apply
```

Migrations live in `database/migrations/`. `bin/migrate.py status` reports the
database's version and anything pending. Cork does not migrate on startup;
deploys run the migration explicitly while Cork is stopped.

## Deploying

`.tangled/workflows/deploy.yml` deploys on every push to `main`. Log in as
`web`, pull each repository, then stop Cork, back up, migrate, and start:

```
set -e
cd /srv/helios && git pull
cd /srv/luna   && git pull
cd /srv/cork   && git pull

uv sync --no-default-groups --group backup
sudo systemctl stop cork.socket cork.service
sudo systemctl start cork-backup.service
sudo -u cork /srv/cork/.venv/bin/python bin/migrate.py apply
sudo systemctl start cork.socket cork.service
```

Starting `cork.service` directly, rather than leaving the socket to activate it
on the first request, makes a failure to boot fail the deploy.
`cork-backup.service` is `Type=oneshot`, so `systemctl start` returns only when
the backup has finished, and fails if it did. `set -e` makes a failed backup or
migration stop the deploy with Cork still stopped, rather than starting it
against a database in an unknown state. The migration runs as `cork` so the
database and its journal stay owned by the service account.

All three projects are installed into the venv as editable `.pth` entries
pointing at their source directories, so a pull is enough to update the code
itself. `uv sync` is only strictly needed when `uv.lock` changed, but it is
fast and idempotent when nothing has, so it is simpler to run it every time
than to decide.

### Restart permission

`web` has no sudo rights, which is deliberate: giving the deploy account
general sudo would undo the separation above, since anyone reaching that
account could then become root. It needs exactly the deploy's privileged
commands, so grant those and nothing else. As the sudo user, once:

```
sudo visudo -f /etc/sudoers.d/cork-deploy
```

```
web ALL=(root) NOPASSWD: /usr/bin/systemctl stop cork.socket cork.service
web ALL=(root) NOPASSWD: /usr/bin/systemctl start cork-backup.service
web ALL=(root) NOPASSWD: /usr/bin/systemctl start cork.socket cork.service
web ALL=(cork) NOPASSWD: /srv/cork/.venv/bin/python bin/migrate.py apply
```

`visudo` validates the syntax before saving; a malformed sudoers file can lock
everyone out of sudo. Each rule matches that exact command only — no other
unit, and no other systemctl verb. The migration rule lets `web` run code as
`cork`, but `web` already owns the code `cork` runs after every restart, so it
grants nothing new.

Stopping the socket means connections are refused while the backup and
migration run. That takes seconds at Cork's size.

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

## Restoring a backup

Backups are `store-YYYY-MM-DD.sqlite.zst` objects under the bucket's prefix.
Each run prints the SHA-256 of the uncompressed snapshot to the
`cork-backup` journal. Restore with Cork stopped:

```
sudo systemctl stop cork.socket cork.service
# download the object, then:
zstd -d store-YYYY-MM-DD.sqlite.zst -o store.sqlite
sha256sum store.sqlite    # compare with the hash in the backup's journal entry
sqlite3 store.sqlite 'PRAGMA integrity_check'    # expect: ok
sudo install -m 0640 -o cork -g cork store.sqlite /var/lib/cork/store.sqlite
sudo rm -f /var/lib/cork/store.sqlite-journal
sudo systemctl start cork.socket cork.service
```

Remove any leftover `store.sqlite-journal` before starting: it belongs to the
replaced database, and SQLite would try to roll it back into the restored one.
Backups taken before the move to SQLite are `store-YYYY-MM-DD.json.zst`; they
age out through normal pruning.

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
`DatabaseError` in the journal straight away.

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
