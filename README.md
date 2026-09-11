# Cork

Cork is a web app for sharing links with your friends.

It is built on the [Helios](https://tangled.org/liamegan.com/helios) framework.

## Layout

- `app/wsgi.py`: wires the `Application`: components run store → views →
  session → flash → guards, then the router.
- `app/main.py`: sets up the devserver.
- `app/http/__init__.py`: the `routes` and `guards` lists.
- `app/http/*.py`: handlebrs, one module per resource.
- `app/data.py`: models and the `schema`.
- `app/views/`: Jinja templates, addressed by dotted path: `boards/show.html`
  is rendered as `"boards.show"`.
- `app/assets/`, `public/static/`: styles and scripts.
- `data/store.json`, `data/sessions.json`: the persisted state.
