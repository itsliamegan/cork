from typing import cast

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.form import Form
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


class SettingsForm(Form):
	open_in_new_tab: bool = False
	return_to: str | None = None


def _settings_return_url(ctx: Context, raw_url: str | None) -> URL:
	urls = ctx.get(URLs)

	match = urls.match(raw_url)
	if match is not None and match.route.name in RETURNABLE_ROUTES:
		return urls.route(match.route.name, match.params)
	else:
		return urls.route("boards.index")


def show(req: Request, ctx: Context) -> Response:
	views = ctx.get(Views)

	return views.render(
		"settings.show",
		{
			"return_to": _settings_return_url(ctx, req.referrer),
		},
	)


def update(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	user = cast(User, auth.user)

	form, errors = SettingsForm.validate(req.input)
	if errors:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	user.open_in_new_tab = form.open_in_new_tab
	store.save(user)

	return Response.redirect(_settings_return_url(ctx, form.return_to))
