from helios.app import Context
from helios.auth import Authenticator
from helios.database import Store
from helios.flash import Flashes
from helios.form import Form, Submissions
from helios.http import Request, Response
from helios.routing import URLs
from helios.view import Views

from app import Invite, Recovery, User


class RedemptionForm(Form):
	token: str
	name: str | None = None


def create(request: Request, context: Context) -> Response:
	store = context.get(Store)
	auth = context.get(Authenticator[User])
	flash = context.get(Flashes)
	submissions = context.get(Submissions)
	urls = context.get(URLs)

	if auth.is_signed_in():
		return Response.redirect(urls.route("home.show"))

	form, errors = RedemptionForm.validate(request.input)
	if errors:
		return Response.redirect(urls.route("redemptions.new"))

	invite = Invite.find_valid(store, form.token)
	if invite is None:
		return Response.redirect(
			urls.route("redemptions.new", query={"token": form.token})
		)

	if invite.target_id is not None:
		user = invite.redeem_for_target(store)
		auth.sign_in(user)
		return Response.redirect(urls.route("boards.index"))

	if form.name is None:
		errors.add("name", "Name must be provided.")
	# The column's NOCASE collation makes this match names that differ only in
	# ASCII case, which is also what its unique constraint rejects.
	elif store.query(User).where({"name": form.name}).exists():
		errors.add("name", "Name is already in use.")
	else:
		user = invite.redeem(store, form.name)
		auth.sign_in(user)
		recovery = Recovery.create(store, user)
		flash["recovery_id"] = str(recovery.id)
		flash["recovery_code"] = recovery.code.plaintext
		return Response.redirect(urls.route("recoveries.show", {"id": recovery.id}))

	submissions.flash(errors, request.input)
	return Response.redirect(urls.route("redemptions.new", query={"token": form.token}))


def new(request: Request, context: Context) -> Response:
	store = context.get(Store)
	auth = context.get(Authenticator[User])
	views = context.get(Views)
	urls = context.get(URLs)

	if auth.is_signed_in():
		return Response.redirect(urls.route("home.show"))

	token = request.url.query.first("token")
	if token is not None:
		invite = Invite.find_valid(store, token)
	else:
		invite = None

	if invite is not None:
		store.load(invite, "creator", "target")

	return views.render(
		"redemptions.new",
		{
			"token": token,
			"invite": invite,
		},
	)
