from urllib.parse import urlsplit

from helios.app import Context
from helios.form import Field, Form, parser
from helios.http import Request, Response, Status, URL


def _settings_return_url(raw_url: str | None) -> URL:
	fallback = URL("/boards/")
	if not isinstance(raw_url, str):
		return fallback

	try:
		path = urlsplit(raw_url).path
	except ValueError:
		return fallback

	if path == "/" or path == "/boards/" or path.startswith(("/boards/", "/pins/")):
		return URL(path)
	return fallback


def show(req: Request, ctx: Context) -> Response:
	html = ctx.views.render(
		"settings.show",
		{
			"current_user": ctx.auth.user,
			"return_to": _settings_return_url(req.referrer),
		},
	)
	return Response.html(html)


def update(req: Request, ctx: Context) -> Response:
	form = Form(
		[
			Field("open_in_new_tab", parser.Bool()),
			Field("return_to", parser.Optional(parser.Str())),
		]
	)
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	ctx.auth.user.open_in_new_tab = input["open_in_new_tab"]
	ctx.store.save(ctx.auth.user)

	return Response.redirect(_settings_return_url(input["return_to"]))
