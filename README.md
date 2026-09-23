# Cork

Cork is a web app for sharing links with your friends.

It is built on the [Helios](https://tangled.org/liamegan.com/helios) framework.

## Layout

- `app/wsgi.py`: wires the `Application`: components run views → session →
  database → flash → auth → guards, then the router.
- `app/main.py`: sets up the devserver.
- `app/http/__init__.py`: the `routes` and `guards` lists.
- `app/http/*.py`: handlebrs, one module per resource.
- `app/data.py`: models and the `models` list.
- `app/views/`: Jinja templates, addressed by dotted path: `boards/show.html`
  is rendered as `"boards.show"`.
- `app/assets/`, `public/static/`: styles and scripts.
- `database/migrations/`: numbered SQL migrations, applied with
  `mise run migrate`.
- `/var/lib/cork/store.sqlite`, `/var/lib/cork/sessions.json`: the persisted
  state, by default. A fresh environment needs `sessions.json` containing `{}`
  and a migrated database.
- `bin/`: the migration runner and backups.
