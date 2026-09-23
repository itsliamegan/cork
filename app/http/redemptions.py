from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.flash import Flashes
from helios.form import Field, Form, parser
from helios.http import Request, Response, URL
from helios.views.engine import Views

from app.data import Invite, Recovery, User


def create(req: Request, ctx: Context) -> Response:
	auth = ctx.get(Authenticator)
	store = ctx.get(Store)
	flash = ctx.get(Flashes)

	if auth.is_signed_in():
		return Response.redirect(URL("/"))

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
		if name == "":
			flash["redemption_error"] = "Enter a name."
			flash["redemption_name"] = ""
			return Response.redirect(URL("/redemptions/new", {"token": token}))

		# The column's NOCASE collation makes this match names that differ only in
		# ASCII case, which is also what its unique constraint rejects.
		if store.query(User).where(name=name).first() is not None:
			flash["redemption_error"] = "That name is already in use."
			flash["redemption_name"] = name
			return Response.redirect(URL("/redemptions/new", {"token": token}))

	user = invite.redeem(store, name)
	auth.sign_in(user)
	if invite.target_id is not None:
		return Response.redirect(URL("/boards/"))
	else:
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
		return Response.redirect(URL("/"))

	token = req.url.query.get("token")
	if not isinstance(token, str):
		return Response.html(views.render("redemptions.new"))

	invite = Invite.find_valid(store, token)
	if invite is None:
		return Response.html(views.render("redemptions.new"))

	context: dict = {"token": token, "invite": invite}

	if invite.target_id is None:
		if "redemption_name" in flash:
			context["name"] = flash["redemption_name"]
		if "redemption_error" in flash:
			context["error"] = flash["redemption_error"]
		context["creator"] = store.find_one(User, invite.creator_id)
	else:
		context["target"] = invite.find_target(store)

	return Response.html(views.render("redemptions.new", context))
