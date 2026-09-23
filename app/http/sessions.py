from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.flash import Flashes
from helios.form import Field, Form, parser
from helios.http import Request, Response, URL
from helios.views.engine import Views

from app.data import Recovery, User


def create(req: Request, ctx: Context) -> Response:
	auth = ctx.get(Authenticator)
	store = ctx.get(Store)
	flash = ctx.get(Flashes)

	if auth.is_signed_in():
		return Response.redirect(URL("/boards/"))

	form = Form([Field("recovery_code", parser.Required(parser.Str()))])
	input, errs = form.validate(req.input)
	if errs:
		flash["session_error"] = "Enter a recovery code."
		return Response.redirect(URL("/sessions/new"))

	code = "".join(input["recovery_code"].split()).upper()
	if len(code) != Recovery.Code.LENGTH or any(
		character not in Recovery.Code.ALPHABET for character in code
	):
		flash["session_error"] = "That recovery code is invalid."
		return Response.redirect(URL("/sessions/new"))

	result = User.recover(store, code)
	if result is None:
		flash["session_error"] = "That recovery code is invalid."
		return Response.redirect(URL("/sessions/new"))

	user, recovery = result
	auth.sign_in(user)
	flash["recovery_id"] = str(recovery.id)
	flash["recovery_code"] = recovery.code.plaintext
	return Response.redirect(URL(f"/recoveries/{recovery.id}"))


def new(req: Request, ctx: Context) -> Response:
	auth = ctx.get(Authenticator)
	flash = ctx.get(Flashes)
	views = ctx.get(Views)

	if auth.is_signed_in():
		return Response.redirect(URL("/boards/"))

	error = None
	if "session_error" in flash:
		error = flash["session_error"]
	return Response.html(views.render("sessions.new", {"error": error}))


def delete(req: Request, ctx: Context) -> Response:
	auth = ctx.get(Authenticator)

	auth.sign_out()
	return Response.redirect(URL("/sessions/new"))
