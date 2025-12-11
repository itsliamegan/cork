from uuid import UUID

from lib.app import Context
from lib.forms import rules, Field, Form
from lib.http import Request, Response, Status, URL

from app.data import Pin

def index(req: Request, ctx: Context) -> Response:
	pins = sorted(ctx.store.find_all(Pin), key = lambda pin: pin.created_at, reverse = True)
	inbox = [pin for pin in pins if not pin.hidden]
	hidden = [pin for pin in pins if pin.hidden]

	html = ctx.views.render("pins.index", {"inbox": inbox, "hidden": hidden})

	return Response.html(html)

def store(req: Request, ctx: Context) -> Response:
	form = Form([
		Field("url", [rules.required]),
		Field("title", [rules.required])
	])
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status = Status.BAD_REQUEST)

	ctx.store.create(Pin, title = input["title"], url = input["url"])

	return Response.redirect(URL("/"))

def new(req: Request, ctx: Context) -> Response:
	html = ctx.views.render("pins.new")
	return Response.html(html)

def edit(req: Request, ctx: Context, params: dict[str, str]) -> Response:
	id = UUID(params["id"])
	pin = ctx.store.find_one(Pin, id)
	if pin is None:
		return Response.text("404 Not Found", status = Status.NOT_FOUND)
	html = ctx.views.render("pins.edit", {"pin": pin})
	return Response.html(html)

def update(req: Request, ctx: Context, params: dict[str, str]) -> Response:
	id = UUID(params["id"])
	pin = ctx.store.find_one(Pin, id)
	if pin is None:
		return Response.text("404 Not Found", status = Status.NOT_FOUND)
	form = Form([
		Field("url", [rules.required]),
		Field("title", [rules.required])
	])
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status = Status.BAD_REQUEST)
	pin.url = input["url"]
	pin.title = input["title"]
	return Response.redirect(URL("/"))
