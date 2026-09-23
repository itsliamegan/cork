from typing import cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.flash import Flashes
from helios.http import Request, Response, URL
from helios.view import Views

from app.data import Recovery, User


def create(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	flash = ctx.get(Flashes)

	user = cast(User, auth.user)
	recovery = Recovery.create(store, user)
	flash["recovery_id"] = str(recovery.id)
	flash["recovery_code"] = recovery.code.plaintext
	return Response.redirect(URL(f"/recoveries/{recovery.id}"))


def show(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	flash = ctx.get(Flashes)
	views = ctx.get(Views)

	user = cast(User, auth.user)
	recovery = Recovery.find_owned(store, id, user)
	if (
		"recovery_id" not in flash
		or flash["recovery_id"] != str(recovery.id)
		or "recovery_code" not in flash
	):
		return Response.redirect(URL("/settings"))

	return Response.html(
		views.render(
			"recoveries.show",
			{
				"current_user": user,
				"recovery_code": flash["recovery_code"],
			},
		)
	)
