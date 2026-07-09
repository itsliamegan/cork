from lux.app import Context
from lux.http import Request, Response

def show(req: Request, ctx: Context) -> Response:
	html = ctx.views.render("settings.show")
	return Response.html(html)
