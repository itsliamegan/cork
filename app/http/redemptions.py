from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.flash import Flashes
from helios.form import Field, Form, parser
from helios.http import Request, Response, URL
from helios.view import Views

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
	if isinstance(token, str):
		invite = Invite.find_valid(store, token)
	else:
		token = None
		invite = None

	creator = None
	target = None
	if invite is not None:
		if invite.target_id is None:
			creator = store.find_one(User, invite.creator_id)
		else:
			target = invite.find_target(store)

	if "redemption_name" in flash:
		name = flash["redemption_name"]
	else:
		name = ""

	if "redemption_error" in flash:
		error = flash["redemption_error"]
	else:
		error = None

	html = views.render(
		"redemptions.new",
		{
			"token": token,
			"invite": invite,
			"creator": creator,
			"target": target,
			"name": name,
			"error": error,
		},
	)
	return Response.html(html)
