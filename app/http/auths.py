from helios.app import Context
from helios.auth import Authenticator
from helios.data.store import Store
from helios.form import Field, Form, parser
from helios.http import Request, Response, Status, URL
from helios.views.engine import Views

from app.data import User


def new(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	views = ctx.get(Views)

	users = store.find_all(User)
	users.sort(key=lambda user: user.name.casefold())
	html = views.render("auths.new", {"users": users})
	return Response.html(html)


def create(req: Request, ctx: Context) -> Response:
	store = ctx.get(Store)
	auth = ctx.get(Authenticator)

	form = Form([Field("user_id", parser.Required(parser.UUID()))])
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)
	user = store.find_one(User, input["user_id"])
	auth.sign_in(user)
	return Response.redirect(URL("/boards/"))


def delete(req: Request, ctx: Context) -> Response:
	auth = ctx.get(Authenticator)

	auth.sign_out()
	return Response.redirect(URL("/sign-in"))
