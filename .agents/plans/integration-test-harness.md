# Integration test harness

## Goal

Add a fast, in-process integration testing harness for Cork that exercises the
real Helios WSGI boundary, middleware/component lifecycle, templates, cookies,
forms, redirects, and JSON persistence without starting a server or controlling
a browser.

Keep the HTTP client generic and small in `helios.wsgi`. Keep application setup,
temporary data, authentication helpers, and model builders in Cork until repeated
use demonstrates that any of them belong in Helios.

## Design boundaries

- Use Werkzeug's WSGI test machinery, which Helios already depends on. Do not
  open sockets or invoke Cork's development server.
- Call the generic Helios wrapper `TestClient` and define it in
  `../helios/src/helios/wsgi.py`.
- Replace Cork's inline application construction with a Cork-specific
  `Application` subclass in `app/__init__.py`; do not introduce a `create_app`
  function.
- Define Cork's test environment as `TestApplication` in `test/support.py`.
- Keep `TestClient` limited to HTTP concerns. It must not know about Cork users,
  models, stores, sign-in routes, or filesystem layout.
- Keep `TestApplication` and Cork's model builders application-specific. Revisit
  extraction only after another Helios application needs the same abstractions.
- Use the real sign-in endpoint for the initial authentication helper so cookie,
  session, auth, redirect, and persistence behavior are all covered together.
- Do not add Selenium or Playwright as part of this work. JavaScript execution,
  Turbo behavior, drag-and-drop, and static-file serving remain outside this
  server integration boundary.

## Helios `TestClient`

### Public API

Add a thin wrapper around `werkzeug.test.Client` in
`../helios/src/helios/wsgi.py`.

1. Construct it with a booted WSGI `Application` and enable Werkzeug's cookie
   jar so response cookies automatically appear on later requests.
2. Provide a general `request` method accepting:
   - a Helios `Method`;
   - a path;
   - optional query parameters;
   - optional URL-encoded form data;
   - optional request headers;
   - optional redirect following.
3. Provide `get`, `post`, `put`, `patch`, and `delete` convenience methods that
   delegate to `request`.
4. Return Werkzeug `TestResponse` objects rather than translating responses back
   into Helios `Response` objects. Tests need the observable WSGI result:
   `status_code`, headers, decoded body, and redirect history.
5. Expose cookie operations needed by tests (`get_cookie`, `set_cookie`, and
   `delete_cookie`) either as explicit delegating methods or by making the
   wrapped Werkzeug client intentionally accessible. Prefer explicit methods so
   common test code does not depend directly on the implementation detail.
6. Accept form values compatible with Werkzeug's `MultiDict`, including repeated
   keys such as Cork's ordered `board_id` collection.
7. Keep an escape hatch for uncommon Werkzeug request options. Either accept
   narrowly typed `**kwargs` in `request` or expose a documented `open` method;
   avoid expanding the wrapper one argument at a time as tests grow.
8. Do not boot the application in `TestClient`. Booting is application lifecycle,
   not HTTP client behavior.

A representative use should read approximately as follows:

```python
client = TestClient(app)
response = client.post(
	"/sign-in",
	form={"user_id": str(user.id)},
)

assert_eq(response.status_code, 302)
assert_eq(response.headers["Location"], "/boards/")
```

### Helios verification

Extend `../helios/test/wsgi_test.py` with focused tests that use a small real
Helios WSGI application and router rather than mocking the Werkzeug client.
Cover:

1. A GET is routed and its status, headers, and decoded body are observable.
2. Query values reach `Request.url.query`.
3. URL-encoded scalar form values reach `Request.input`.
4. Repeated form keys reach `Request.input` as a list in submission order.
5. Cookies set by one response are sent on the next request.
6. Redirects are returned without following by default and are followed when
   explicitly requested, with response history retained.
7. Each convenience method emits the corresponding Helios method.
8. Browser-style method override remains testable by posting a `_method` form
   field; do not make the convenience methods silently use method override.

Use the existing Luna assertions and test command. Run the complete Helios suite,
not only the new WSGI tests.

## Cork `Application` subclass

Refactor `app/__init__.py` so Cork owns an `Application` subclass of
`helios.wsgi.Application`.

1. Alias the imported Helios class to make the inheritance relationship clear.
2. Give the Cork subclass constructor configurable paths for:
   - the store JSON file;
   - the sessions JSON file;
   - the views directory.
3. Default those paths to Cork's production locations, anchored to the project or
   package location rather than relying on the process's current working
   directory. This allows both `mise run serve` and tests invoked from other
   directories to resolve the same resources predictably.
4. In the constructor, assemble the existing router and components in their
   current order: store, views, session, flash, auth.
5. Preserve the module-level WSGI entry point by constructing `app = Application()`
   and booting it once.
6. Keep `main()` and development static-file/reloader setup functionally
   unchanged. The integration harness tests Cork's WSGI application; it does not
   test Werkzeug's development-only static mapping.
7. Keep booting explicit. `Application.__init__` should configure the application,
   while the production module and `TestApplication` each call `boot()` for the
   instance they own.

## Cork `TestApplication`

Create `test/support.py` with a context-managed `TestApplication` that owns all
resources for one test.

### Lifecycle and exposed state

1. Allocate a `TemporaryDirectory` on entry/construction and retain it until the
   context exits.
2. Create isolated files containing the valid empty representations expected by
   Helios:
   - `store.json`: `[]`;
   - `sessions.json`: `{}`.
3. Construct Cork's `Application` with those temporary files and the real Cork
   views directory, then boot it.
4. Construct and expose a Helios `TestClient` for the booted application.
5. Clean up the temporary directory on exit, including when an assertion or
   request raises.
6. Do not share an application, component instance, store file, session file, or
   cookie jar between tests.
7. Expose the temporary paths when useful for diagnostics, but make tests prefer
   higher-level state helpers over direct JSON manipulation.

The intended test shape is:

```python
with TestApplication() as test:
	user = test.create_user(name="Alice")
	test.sign_in(user)

	response = test.client.post(
		"/boards/",
		form={"title": "Reading"},
	)

	assert_eq(response.status_code, 302)
	assert_eq(test.find_all(Board)[0].title, "Reading")
```

### Store access and builders

Build only the small set of Cork conveniences needed by the first integration
tests, then add more as feature tests demand them.

1. Provide a fresh-store accessor that calls `helios.store.load` with Cork's
   schema every time persisted state is inspected. Do not retain
   `ctx.store` or an old `Store` object across requests, because each request
   loads a new object graph and saves it afterward.
2. Provide a generic persistence helper internally that loads the current store,
   creates a model through `Store.create`, saves it, and returns the created
   model.
3. Initially expose `create_user`, with defaults matching Cork's model
   requirements. Add focused `create_board`, `create_pin`, `share_board`, and
   ordering builders only alongside tests that need them rather than designing a
   large speculative factory API.
4. Let `Store.create` generate IDs and timestamps so seeded records use the same
   model construction path as application-created records.
5. Accept model objects in relationship-oriented builder arguments (for example,
   an owner rather than a raw `user_id`) and translate to IDs inside support code.
   This keeps individual tests legible while the persisted model remains real.
6. Provide small read helpers such as `find_all` and, if immediately useful,
   `find_one`; each helper must load the latest persisted store first.
7. Do not mutate a model returned before a request and expect that mutation to
   affect later requests. Reload persisted models before post-request assertions.

### Authentication helper

Implement `sign_in(user)` by posting the real `POST /sign-in` form through the
same client.

1. Submit `user_id` as a URL-encoded value.
2. Assert inside the helper that sign-in returns the expected redirect to
   `/boards/`; a failed setup should stop the test close to its cause.
3. Rely on `TestClient`'s cookie jar for subsequent authenticated requests.
4. Do not initially seed session JSON or manufacture a session cookie. Add a
   lower-level authentication shortcut only if real sign-in becomes a material
   source of noise or if tests specifically need pre-existing session state.
5. Tests of sign-in itself should call the client directly rather than using the
   helper whose behavior they are verifying.

## Cork test suite and tooling

1. Create Cork's `test/` package/directory with `test/support.py` and an initial
   integration test module following Luna's `*_test.py` discovery convention.
2. Add Luna as a Cork development dependency using the adjacent editable source,
   matching Helios's existing test setup.
3. Add a `test` task to Cork's `mise.toml` that runs `uv run -m luna.test.runner`.
4. Update Cork's lockfile through `uv` rather than editing it manually.
5. Keep support modules from being mistaken for test modules by naming the file
   `support.py`, not `support_test.py`.

Start with a small vertical set of retained integration tests:

1. An unauthenticated request to `/boards/` redirects to `/sign-in`.
2. A user can sign in through the real endpoint, retain the session cookie, and
   load `/boards/` as rendered HTML.
3. A signed-in user can create a board through `POST /boards/`; assert the
   redirect and reload the temporary store to verify ownership and title.
4. A browser-style `_method=DELETE` request deletes that board and redirects to
   `/boards/`.
5. At least one redirect-following test verifies the final rendered response and
   response history without manually replaying cookies.

These tests establish the harness across routing, guards, forms, views, store,
session, auth, cookies, redirects, method override, and WSGI adaptation without
attempting comprehensive Cork feature coverage in the same change.

## Unexpected exceptions

Helios currently converts unexpected exceptions to `500 Internal Server Error`
inside `helios.app.capture_errors`. Do not silently make `TestClient` raise for
every 500: a client sees only the HTTP result and no longer has the original
exception, and some tests may intentionally exercise a 500 response.

Treat configurable exception propagation as a follow-up framework improvement
rather than coupling it to the initial client. For the initial harness:

- the existing middleware prints the original traceback, which Luna captures;
- retained happy-path integration tests must fail if they receive a 500 instead
  of their expected response;
- if debugging hidden exceptions proves painful, add an explicit Helios
  application option that omits only the unexpected-exception capture middleware
  in tests while preserving HTTP error conversion and component `after` hooks.

## Verification

### Automated

1. From `../helios`, run `mise run test` and `mise run lint`.
2. From Cork, run the new `mise run test` and existing `mise run lint`.
3. Run the Cork suite more than once to confirm temporary persistence and cookie
   state do not leak between tests.
4. Run an individual Cork test through Luna's name filter to confirm the support
   module has no import-order dependency on the production global `app`.

### Manual structural checks

1. Import Cork's module-level `app` and confirm it remains a callable WSGI
   application.
2. Confirm `mise run serve` still uses the production data, views, reloader, and
   static mappings without starting a second application accidentally.
3. Confirm deleting or corrupting a temporary test directory cannot affect
   `data/store.json` or `data/sessions.json`.

## Deferred scope

- Full feature-by-feature Cork integration coverage.
- Browser execution for Turbo, Stimulus, drag-and-drop, or accessibility-tree
  behavior.
- JavaScript unit tests.
- Testing development-server static-file mappings.
- A generic Helios model-builder or application-fixture abstraction.
- Parallel-safe production JSON persistence; test isolation here prevents tests
  from sharing files but does not change the store's concurrency model.
