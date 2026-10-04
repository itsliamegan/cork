from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.flash import Flashes
from helios.form import Filters, Form, Rules, Submissions
from helios.form.filter import Unspace, Upcase
from helios.form.rule import Length, Only
from helios.http import Request, Response
from helios.routing import URLs
from helios.view import Views

from app import Recovery, User


class SignInForm(Form):
	filters = Filters({"recovery_code": [Unspace(), Upcase()]})
	rules = Rules(
		{
			"recovery_code": [
				Only(Recovery.Code.ALPHABET),
				Length(exactly=Recovery.Code.LENGTH),
			],
		}
	)

	recovery_code: str


def create(request: Request, context: Context) -> Response:
	store = context.get(Store)
	auth = context.get(Authenticator[User])
	flash = context.get(Flashes)
	submissions = context.get(Submissions)
	urls = context.get(URLs)

	if auth.is_signed_in():
		return Response.redirect(urls.route("boards.index"))

	form, errors = SignInForm.validate(request.input)
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


def new(request: Request, context: Context) -> Response:
	auth = context.get(Authenticator[User])
	views = context.get(Views)
	urls = context.get(URLs)

	if auth.is_signed_in():
		return Response.redirect(urls.route("boards.index"))

	return views.render("sessions.new")


def delete(request: Request, context: Context) -> Response:
	auth = context.get(Authenticator[User])
	urls = context.get(URLs)

	auth.sign_out()
	return Response.redirect(urls.route("sessions.new"))
