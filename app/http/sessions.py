from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.flash import Flashes
from helios.form import Form, RuleError, Submissions
from helios.http import Request, Response
from helios.routing import URLs
from helios.view import Views

from app import Recovery


class RecoveryCode:
	name = "recovery_code"
	message = "is invalid"

	def check(self, value: str) -> str:
		code = "".join(value.split()).upper()
		if len(code) != Recovery.Code.LENGTH or any(
			character not in Recovery.Code.ALPHABET for character in code
		):
			raise RuleError()
		else:
			return code


class SignInForm(Form):
	rules = {"recovery_code": [RecoveryCode()]}

	recovery_code: str


def create(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)
	flash = ctx.get(Flashes)
	submissions = ctx.get(Submissions)
	urls = ctx.get(URLs)

	if auth.is_signed_in():
		return Response.redirect(urls.route("boards.index"))

	form, errors = SignInForm.validate(req.input)
	if errors:
		submissions.flash(errors)
		return Response.redirect(urls.route("sessions.new"))

	result = Recovery.redeem(store, form.recovery_code)
	if result is None:
		errors.add("recovery_code", "Recovery code is invalid.")
		submissions.flash(errors)
		return Response.redirect(urls.route("sessions.new"))

	user, recovery = result
	auth.sign_in(user)
	flash["recovery_id"] = str(recovery.id)
	flash["recovery_code"] = recovery.code.plaintext
	return Response.redirect(urls.route("recoveries.show", {"id": recovery.id}))


def new(req: Request, ctx: Context) -> Response:
	auth = ctx.get(Authenticator)
	views = ctx.get(Views)
	urls = ctx.get(URLs)

	if auth.is_signed_in():
		return Response.redirect(urls.route("boards.index"))

	return views.render("sessions.new")


def delete(req: Request, ctx: Context) -> Response:
	auth = ctx.get(Authenticator)
	urls = ctx.get(URLs)

	auth.sign_out()
	return Response.redirect(urls.route("sessions.new"))
