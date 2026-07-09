from uuid import UUID

from lux.app import Context
from lux.forms import rules, Field, Form
from lux.http import Request, Response, Status, URL

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
	user_id = UUID(input["user_id"])
	return Response.redirect(URL("/boards/"))

def delete(req: Request, ctx: Context) -> Response:
	ctx.session.clear()
	return Response.redirect(URL("/sign-in"))
