from typing import cast

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.flash import Flashes
from helios.form import Field, Form, parser
from helios.http import Request, Response, Status, URL
from helios.routing import URLs
from helios.view import Views

from app import User

RETURNABLE_ROUTES = {
	"home.show",
	"boards.index",
	"boards.show",
	"pins.index",
	"pins.show",
}


def _settings_return_url(ctx: Context, raw_url: str | None) -> URL:
	urls = ctx.get(URLs)

	match = urls.match(raw_url)
	if match is not None and match.route.name in RETURNABLE_ROUTES:
		return urls.route(match.route.name, match.params)
	else:
		return urls.route("boards.index")


def show(req: Request, ctx: Context) -> Response:
	flash = ctx.get(Flashes)
	views = ctx.get(Views)

	invite_error = None
	if "invite_error" in flash:
		invite_error = flash["invite_error"]
	return views.render(
		"settings.show",
		{
			"invite_error": invite_error,
			"return_to": _settings_return_url(ctx, req.referrer),
		},
	)


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

	return Response.redirect(_settings_return_url(ctx, input["return_to"]))
