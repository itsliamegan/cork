from typing import cast
from uuid import UUID

from helios.app import Context
from helios.auth import Authenticator
from helios.data.store import Store
from helios.flash import Flashes
from helios.form import Field, Form, parser
from helios.http import Request, Response, URL
from helios.views.engine import Views

from app.data import Invite, User


def create(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	flash = ctx.get(Flashes)

	form = Form([Field("targeted", parser.Bool())])
	input, errs = form.validate(req.input)
	if errs:
		flash["invite_error"] = "Choose an invite type."
		return Response.redirect(URL("/settings"))

	creator = cast(User, auth.user)
	invite = Invite.create(
		store,
		creator,
		target=creator if input["targeted"] else None,
	)
	flash["invite_id"] = str(invite.id)
	flash["invite_token"] = invite.token.value
	return Response.redirect(URL(f"/invites/{invite.id}"))


def show(req: Request, ctx: Context, id: UUID) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	flash = ctx.get(Flashes)
	views = ctx.get(Views)

	creator = cast(User, auth.user)
	invite = Invite.find_created_by(store, id, creator)
	if (
		"invite_id" not in flash
		or flash["invite_id"] != str(invite.id)
		or "invite_token" not in flash
	):
		return Response.redirect(URL("/settings"))

	token = flash["invite_token"]
	return Response.html(
		views.render(
			"invites.show",
			{
				"current_user": creator,
				"invite": invite,
				"invite_link": str(URL("/redemptions/new", {"token": token})),
			},
		)
	)
