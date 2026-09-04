from uuid import UUID

from helios.app import Context
from helios.forms import rules, Field, Form
from helios.http import Request, Response, Status, URL

from app.data import User

def new(req: Request, ctx: Context) -> Response:
	users = ctx.store.find_all(User)
	html = ctx.views.render("auths.new", {"users": users})
	return Response.html(html)

def create(req: Request, ctx: Context) -> Response:
	form = Form([
		Field("user_id", [rules.required])
	])
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status = Status.BAD_REQUEST)
	user = ctx.store.find_one(User, UUID(input["user_id"]))
	if not user:
		return Response.text("400 Bad Request", status = Status.BAD_REQUEST)
	ctx.auth.sign_in(user)
	return Response.redirect(URL("/boards/"))

def delete(req: Request, ctx: Context) -> Response:
	ctx.auth.sign_out()
	return Response.redirect(URL("/sign-in"))
