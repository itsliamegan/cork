# Helios configuration

## Goal

Move environment resolution out of the application and into Helios, so an app
declares what it needs and Helios resolves it. Today each Helios module exposes
a `Config` holding one or two `Path`s, and every application rewrites the
lookup, defaults, precedence, and dotenv merging around them. In Cork this is
`app/config.py`: roughly 75 lines to configure four paths, 40 of them a
`from_env` of near-identical `Path(environ.get(NAME, DEFAULT_CONFIG.x.y))`
blocks.

## Design

1. Make the environment variable name part of the declaration rather than a
   string repeated at the call site. Section plus field yields `CORK_VIEWS_DIR`;
   defaults are supplied where the application composes its config, since that
   is where the layout is known. `from_env` and the `DEFAULT_CONFIG` singleton
   both disappear.
2. Report configuration errors as configuration errors. Once the name-to-field
   mapping is recorded, missing and invalid values can be aggregated into one
   message naming the variable. Today `environ.get` with a default cannot fail,
   so a mistyped variable silently falls back and surfaces much later as an
   empty store.
3. Accept the environment file as a parameter to `load`, symmetric with the
   existing `environ` parameter, instead of hardcoding `ROOT_DIR/.env`.
4. State the precedence in Helios rather than leaving each application to
   reconstruct it. Cork's `dotenv_values`, drop-`None`, then `update(environ)`
   encodes a real decision — the process environment wins — that should be
   documented once.
5. Support types beyond `Path`, at least `int`, `bool`, and a redacting
   `secret`. Cork is all paths today, but the next variable is a port, a session
   lifetime, or a token, and `bool` parsing from the environment is a familiar
   source of mistakes.
6. Keep the `Config` types free of third-party imports, in leaf modules beside
   the components they configure. Reading Cork's four paths currently loads 188
   modules, nearly all of them Jinja, because `app/config.py` imports
   `helios.views` for a four-line class.

## Non-goals

1. No global config object or string-keyed lookup. Components should continue to
   receive their `Config` explicitly; this concerns only how one is built.
2. No layered file formats. Environment plus an optional dotenv file is the
   right scope.
3. No behaviour on `Config` itself — no filesystem access or store reads during
   construction.

## Verification

1. Cork's `app/config.py` reduces to declarations with defaults and no
   per-variable environment plumbing.
2. A mistyped or malformed variable fails at load with a message naming it,
   rather than falling back to a default.
3. Importing an application's config does not import Jinja.
4. A script outside the application package — `bin/backup.py` is the immediate
   case — can load the same configuration, pointed at its own environment file,
   without importing routes, models, or views.
