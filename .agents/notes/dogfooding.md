# Dogfooding notes

Observations made while implementing features in Cork. These are notes about
friction, not necessarily prescriptions; revisit them after seeing repeated
patterns.

## Helios framework

### Forms have no bound rendering story

A form does not retain submitted values and errors for a template. Even the
simple required-title failure therefore becomes a generic `400 Bad Request`
instead of re-rendering the page with the submitted state and useful feedback.
GET handlers/templates and POST handlers would have to assemble that state by
hand to provide friendly validation errors.

Forms also stop at parsing individual fields. Domain validation remains in the
handler: for example, the new-board form can parse recipient UUIDs, but the
handler must separately load the available users, reject the owner and unknown
IDs, and deduplicate the selection. This makes it especially important to
finish all validation before mutating the store.

### Relationship-derived reads are assembled by hand

Transactions, foreign keys, cascades, and unique constraints now live in SQL,
so deletion loops and check-then-create races are gone. What remains is reading
across relationships: there is no join, projection, or relationship-loading
API, so handlers load one model, collect IDs, and fetch the related model with
`where_in`, joining in Python. `where_in` keeps each step to one indexed query
rather than a full scan, but the same collect-and-fetch pattern repeats across
`boards.show`, `pins.index`, `build_board_options`, and `find_accessible_pin`.
Counting is the sharpest case; see below.

### Every signed-in request is a database writer

Resolving the `Store` opens `BEGIN IMMEDIATE`, and the auth provider resolves
the `Store` on every signed-in request to load the user. So requests that only
read still take SQLite's write lock and serialize across workers. WAL mode
would not help while that holds. A deferred transaction, upgraded on the first
write, would let reads run concurrently.

### Session and database locks are taken in resolution order

The session provider holds its file lock from the moment the session `Store` is
resolved until the request ends. The auth provider resolves the session before
the database `Store`, so today every request takes the session lock first. A
handler that resolved the database `Store` before anything touched the session
would take the two locks in the opposite order, and two such requests could
block each other until SQLite's busy timeout. Nothing enforces the order.

The session lock also means requests already serialize on the session file, so
Cork's concurrent-redemption test never contends on `BEGIN IMMEDIATE`.

### `Store.insert` always sets `created_at`

`insert` overwrites `created_at` with the current time, and nothing accepts an
existing value. There is no supported way to import historical records; an
importer has to bypass `Store` and write rows with raw SQL, repeating its
encoding and quoting.

### The session file driver fails when its file is missing

`helios.session.file.Driver` raises `DriverError` if `sessions.json` does not
exist, so every fresh environment has to create it by hand as `{}`. An absent
file could be treated as an empty store, as the save path already tolerates.

### Related-record counts have no query form

`pins.index` shows how many boards each pin is on, so it loads every placement
row just to count them. `Store.select()` cannot carry the count because
hydration rejects any column that is not a model attribute, so
`SELECT pins.*, COUNT(...) AS board_count` fails. A per-pin `count()` would be
N+1. The only SQL-side option is hand-written `GROUP BY` against
`store.connection`, which means guarding empty `IN ()` lists, encoding UUIDs
by hand, decoding result keys and closing the cursor.

A narrow grouped count would cover this without relationships or relaxed
hydration, matching Rails' `where(...).group(:pin_id).count`:

```python
store.query(Placement).where_in("pin_id", pin_ids).count_by("pin_id")
# -> {UUID(...): 2, UUID(...): 1}
```

It depends on `where_in`, and keys would be decoded with the named attribute's
type. With `where_in` alone, Python-side counting only loads the current user's
rows, which is fine at Cork's scale; revisit if a second grouped count appears.

### There is no schema or migration story

Helios has a SQLite database layer but nothing that creates or evolves the
schema, so every application needs its own runner. Cork's `lib/migrate.py`
(forward-only SQL files, `PRAGMA user_version`, one transaction per migration)
depends only on `helios.database` and is written to move into Helios once its
shape has settled.

### Safe return URLs are repeated application plumbing

`Request.referrer` exposes the raw `Referer` string, while `URL` represents only
a path and query. Returning to the previous page after board or settings edits
therefore requires each resource to parse the referrer, choose an allowlist and
fallback, carry the result through a hidden form field, and validate the
user-controlled value again before redirecting. A small framework-level helper
for resolving safe local return targets would reduce duplicated security-sensitive
code and make the intended origin/path handling explicit.

