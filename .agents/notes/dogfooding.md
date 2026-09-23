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

### Relationships and uniqueness are entirely application concerns

The store has no relationship, cascade, or uniqueness primitives. This is
consistent with its small scope, but sharing requires manual joins, duplicate
checks, and explicit cascade-deletion loops for both pins and shares. Updating a
board and reconciling several `Share` records also has no transaction or
rollback boundary, so the handler must validate the complete change before it
starts mutating the store. Concurrent request safety may also matter because
uniqueness is check-then-create against a JSON file.

Relationship-derived views can require broad reads. Determining whether each
accessible board is private or shared requires loading every accessible board
and every `Share`, then joining them with an ID set in application code. There
is no `exists`, projection, grouping, or relationship-loading API. This is
reasonable for the current JSON store size, but the same joins are easy to
repeat across handlers and become full scans as data grows.

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

## Cork application architecture

### There is no Cork test harness yet

Cork has no test directory, test command, request client, or fixtures for a
booted application, component context, temporary store, authenticated session,
or rendered response. Handler checks during feature work require ad hoc
contexts and fake views. A proper harness should exercise the real request and
component lifecycle before application tests are retained.
