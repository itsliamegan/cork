from helios.app import Context
from helios.form import Field, Form, parser
from helios.http import Request, Response, Status


def show(req: Request, ctx: Context) -> Response:
	html = ctx.views.render("settings.show", {"user": ctx.auth.user})
	return Response.html(html)


def update(req: Request, ctx: Context) -> Response:
	form = Form([Field("open_in_new_tab", parser.Bool())])
	input, errs = form.validate(req.input)
	if errs:
		return Response.text("400 Bad Request", status=Status.BAD_REQUEST)

	ctx.auth.user.open_in_new_tab = input["open_in_new_tab"]

	return Response.redirect("/settings")
