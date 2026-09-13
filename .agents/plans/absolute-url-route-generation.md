# Absolute URL and route generation

## 1. Desired outcome and user-visible behavior

- Helios can represent complete absolute URLs as well as relative URLs.
- Helios can generate URLs from named routes.
- Route generation produces absolute URLs by default using Cork's required `APP_URL`.
- Callers can explicitly request a relative URL.
- Cork's invite page receives a complete redemption URL from the server.
- The invite link no longer depends on JavaScript to become absolute.

## 2. Scope and non-goals

### In scope

- Scheme, host, optional port, path, and query support in Helios URLs.
- Named routes and reverse generation.
- Route parameters, group prefixes, and query parameters in generated URLs.
- A configured public base URL supplied by Cork.
- Naming Cork's routes so each is available for generation.
- Migrating the invite link to the route helper.
- Removing the obsolete client-side URL expansion.

### Non-goals

- Deriving the origin from request headers.
- Trusted-host or trusted-proxy handling.
- URL fragments or embedded user credentials.
- Supporting applications mounted beneath a path prefix.
- Migrating every existing Cork redirect and navigation link to route helpers.

## 3. Confirmed decisions and assumptions

- `APP_URL` is mandatory in Cork.
- The route helper generates absolute URLs by default.
- Relative generation is explicitly requested.
- Routes use stable string names rather than handler references.
- `APP_URL` is expected to identify the application's origin.
- Helios will not check whether `APP_URL` contains a path prefix; behavior in that case is unsupported.
- Helios receives the configured URL as a value and does not read Cork's environment itself.

An intended interface resembles:

```python
urls.route(
	"redemptions.new",
	query={"token": token},
)
```

Relative generation resembles:

```python
urls.route(
	"boards.index",
	absolute=False,
)
```

The exact API can be refined during implementation.

## 4. Scenarios and acceptance criteria

### URL representation

- A path and query still stringify exactly as before.
- A scheme and host produce an absolute URL.
- An optional non-default port is preserved.
- Query parameters continue to use proper percent encoding.
- Existing uses of `URL("/path")` remain compatible.

### Reverse routing

- A named route without parameters generates its complete grouped path.
- A route such as `/{id:uuid}` substitutes and encodes the supplied value.
- Group prefixes are included exactly once.
- Query parameters are independent of route parameters.
- Missing route names and missing or unexpected parameters fail clearly.
- Duplicate route names are rejected when the router is constructed.
- Absolute generation uses the configured public URL.
- `absolute=False` returns a relative URL.

### Cork

- Missing or blank `APP_URL` prevents startup.
- The test application supplies a deterministic origin.
- The server-rendered invite response contains the full configured origin, redemption path, and token.
- The Copy button copies the already-absolute link.
- Existing relative redirects remain unchanged.

## 5. Delivery steps

1. Extend Helios's URL value to model the components needed for absolute URLs while preserving existing construction and stringification.
2. Add route names and reverse path generation to Helios routing.
3. Add an origin-aware route-generation facility available through the request context.
4. Require Cork's `APP_URL` and supply it to that facility during application construction.
5. Give Cork routes stable names.
6. Migrate the invite handler to generate the redemption URL by route name.
7. Remove the copy controller behavior that rewrites anchor text from the browser-resolved `href`.
8. Update Cork's example and deployed configuration expectations for `APP_URL`.

## 6. Validation approach

- Add focused Helios tests for absolute URL formatting.
- Add routing tests for names, grouped paths, typed parameters, query parameters, relative generation, and error cases.
- Preserve all existing Helios URL and routing tests.
- Add Cork configuration tests for the required value.
- Add an invite integration test that inspects the raw response body.
- Run both Helios and Cork test suites and linters.

## 7. Open questions or decisions still needing review

None currently. The path-prefix case is intentionally unsupported and unchecked.
