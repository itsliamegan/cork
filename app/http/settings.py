from typing import cast
from urllib.parse import urlsplit

from helios.app import Context
from helios.auth import Authenticator
from helios.data.store import Store
from helios.flash import Flashes
from helios.form import Field, Form, parser
from helios.http import Request, Response, Status, URL
from helios.views.engine import Views

from app.data import Recovery, User


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
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	flash = ctx.get(Flashes)
	user = cast(User, auth.user)
	views = ctx.get(Views)

	invite_error = None
	if "invite_error" in flash:
		invite_error = flash["invite_error"]
	html = views.render(
		"settings.show",
		{
			"current_user": user,
			"invite_error": invite_error,
			"has_recovery": Recovery.exists_for(store, user),
			"return_to": _settings_return_url(req.referrer),
		},
	)
	return Response.html(html)


def update(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)

	form = Form(
		[
			Field("open_in_new_tab", parser.Bool()),
			Field("return_to", parser.Optional(parser.Str())),
		]
	)
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	user.open_in_new_tab = input["open_in_new_tab"]
	store.save(user)

	return Response.redirect(_settings_return_url(input["return_to"]))
