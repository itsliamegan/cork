from helios.app import Context
from helios.auth import Authenticator
from helios.data.store import Store
from helios.flash import Flashes
from helios.form import Field, Form, parser
from helios.http import Request, Response, Status, URL
from helios.views.engine import Views

from app.data import InvalidInviteError, Invite, Recovery, User


def create(req: Request, ctx: Context) -> Response:
	auth = ctx.get(Authenticator)
	store = ctx.get(Store)
	flash = ctx.get(Flashes)

	if auth.is_signed_in():
		return Response.redirect(URL("/boards/"))

	form = Form(
		[
			Field("token", parser.Required(parser.Str())),
			Field("name", parser.Optional(parser.Str())),
		]
	)
	input, errs = form.validate(req.input)
	if errs:
		flash["redemption_error"] = "This invite link is invalid."
		return Response.redirect(URL("/redemptions/new"))

	token = input["token"]
	invite = Invite.find_valid(store, token)
	if invite is None:
		return Response.redirect(URL("/redemptions/new", {"token": token}))

	name = (input["name"] or "").strip()
	if invite.target_id is None:
		if not name:
			flash["redemption_error"] = "Enter a display name."
			flash["redemption_name"] = name
			return Response.redirect(URL("/redemptions/new", {"token": token}))

		folded_name = name.casefold()
		if any(user.name.casefold() == folded_name for user in store.find_all(User)):
			flash["redemption_error"] = "That display name is already in use."
			flash["redemption_name"] = name
			return Response.redirect(URL("/redemptions/new", {"token": token}))

	try:
		user = invite.redeem(store, name)
	except InvalidInviteError:
		return Response.redirect(URL("/redemptions/new", {"token": token}))

	auth.sign_in(user)
	if invite.target_id is not None:
		return Response.redirect(URL("/boards/"))

	recovery = Recovery.create(store, user)
	flash["recovery_id"] = str(recovery.id)
	flash["recovery_code"] = recovery.code.plaintext
	return Response.redirect(URL(f"/recoveries/{recovery.id}"))


def new(req: Request, ctx: Context) -> Response:
	views = ctx.get(Views)
	auth = ctx.get(Authenticator)
	store = ctx.get(Store)
	flash = ctx.get(Flashes)

	if auth.is_signed_in():
		return Response.html(views.render("redemptions.new"), status=Status.NOT_FOUND)

	token = req.url.query.get("token")
	if not isinstance(token, str):
		return Response.html(views.render("redemptions.new"), status=Status.NOT_FOUND)

	invite = Invite.find_valid(store, token)
	if invite is None:
		return Response.html(views.render("redemptions.new"), status=Status.NOT_FOUND)

	context: dict = {"token": token, "invite": invite}

	if invite.target_id is None:
		if "redemption_name" in flash:
			context["name"] = flash["redemption_name"]
		if "redemption_error" in flash:
			context["error"] = flash["redemption_error"]
		context["creator"] = store.find_one(User, invite.creator_id)
	else:
		try:
			context["target"] = invite.find_target(store)
		except InvalidInviteError:
			return Response.html(
				views.render("redemptions.new"), status=Status.NOT_FOUND
			)

	return Response.html(views.render("redemptions.new", context))
