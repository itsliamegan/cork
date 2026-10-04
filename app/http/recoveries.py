from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.flash import Flashes
from helios.http import Request, Response
from helios.routing import URLs
from helios.view import Views

from app import Recovery, User


def create(request: Request, context: Context) -> Response:
	store = context.get(Store)
	auth = context.get(Authenticator[User])
	flash = context.get(Flashes)
	urls = context.get(URLs)

	recovery = Recovery.create(store, auth.user)
	flash["recovery_id"] = str(recovery.id)
	flash["recovery_code"] = recovery.code.plaintext
	return Response.redirect(urls.route("recoveries.show", {"id": recovery.id}))


def show(request: Request, context: Context, id: UUID) -> Response:
	store = context.get(Store)
	auth = context.get(Authenticator[User])
	flash = context.get(Flashes)
	views = context.get(Views)
	urls = context.get(URLs)

	recovery = Recovery.find_owned(store, id, auth.user)
	if (
		"recovery_id" not in flash
		or flash["recovery_id"] != str(recovery.id)
		or "recovery_code" not in flash
	):
		return Response.redirect(urls.route("settings.show"))

	return views.render(
		"recoveries.show",
		{
			"recovery_code": flash["recovery_code"],
		},
	)
